"""
JSON Parser for Curriculum Data
Converts JSON curriculum structure to CSV-compatible format for scheduler
"""

import json
import pandas as pd
from typing import Dict, List, Tuple


class CurriculumJSONParser:
    """Parse curriculum JSON files and convert to scheduler-compatible format."""
    
    def __init__(self, json_file: str):
        """Initialize parser with JSON file."""
        self.json_file = json_file
        self.data = self._load_json()
        
    def _load_json(self) -> Dict:
        """Load JSON file."""
        with open(self.json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def extract_courses(self) -> pd.DataFrame:
        """
        Extract courses from JSON and convert to CSV format.
        
        Returns DataFrame with columns:
        - code: Course code
        - name: Course name
        - program: Program (IT/IS)
        - year: Year level
        - lec_hours: Lecture hours
        - lab_hours: Laboratory hours
        - room_type_required: Required room type
        """
        courses = []
        program = self.data.get('program', 'IT')
        curriculum = self.data.get('curriculum', {})
        
        # Parse each year
        year_mapping = {
            'first_year': 1,
            'second_year': 2,
            'third_year': 3,
            'fourth_year': 4
        }
        
        for year_key, year_num in year_mapping.items():
            if year_key not in curriculum:
                continue
                
            year_data = curriculum[year_key]
            
            # Parse each semester
            for semester_key in ['first_semester', 'second_semester']:
                if semester_key not in year_data:
                    continue
                    
                semester_data = year_data[semester_key]
                subjects = semester_data.get('subjects', [])
                
                for subject in subjects:
                    # Determine room type based on course characteristics
                    room_type = self._determine_room_type(
                        subject['code'], 
                        subject['description'],
                        subject['lab']
                    )
                    
                    courses.append({
                        'code': subject['code'].replace(' ', ''),
                        'name': subject['description'],
                        'program': 'IT',  # From JSON
                        'year': year_num,
                        'lec_hours': subject['lec'],
                        'lab_hours': subject['lab'],
                        'room_type_required': room_type
                    })
        
        # Skip elective courses - they are not auto-scheduled
        # Only the placeholder ITELECT courses in curriculum are used
        # Students vote on which specific electives (IT 129-140) to offer
        # Those get manually added based on voting results
        
        return pd.DataFrame(courses)
    
    def _determine_room_type(self, code: str, description: str, lab_hours: int) -> str:
        """
        Determine required room type based on course characteristics.
        
        Returns: Room type string (programming, database, networking, etc.)
        """
        code_upper = code.upper()
        desc_lower = description.lower()
        
        # Mapping based on course content
        if 'network' in desc_lower or 'NETWORKING' in code_upper:
            return 'networking'
        elif 'database' in desc_lower or 'DATABASE' in code_upper:
            return 'database'
        elif 'security' in desc_lower or 'cyber' in desc_lower:
            return 'security'
        elif 'mobile' in desc_lower or 'android' in desc_lower or 'ios' in desc_lower:
            return 'mobile_dev'
        elif 'web' in desc_lower or 'internet' in desc_lower:
            return 'web_dev'
        elif 'system' in desc_lower and 'admin' in desc_lower:
            return 'systems'
        elif 'programming' in desc_lower or 'code' in code_upper or lab_hours > 0:
            return 'programming'
        elif 'graphic' in desc_lower or 'animation' in desc_lower or 'art' in desc_lower:
            return 'multimedia'
        else:
            return 'general'
    
    def save_to_csv(self, output_file: str):
        """Save extracted courses to CSV file."""
        df = self.extract_courses()
        df.to_csv(output_file, index=False)
        return df
    
    def get_summary(self) -> Dict:
        """Get summary statistics of curriculum."""
        df = self.extract_courses()
        
        summary = {
            'total_courses': len(df),
            'total_units': self.data.get('total_units', 0),
            'courses_by_year': df.groupby('year').size().to_dict(),
            'courses_by_room_type': df.groupby('room_type_required').size().to_dict(),
            'total_lec_hours': df['lec_hours'].sum(),
            'total_lab_hours': df['lab_hours'].sum()
        }
        
        return summary


def create_sample_enrollment_from_json(json_file: str, output_file: str = 'enrollment.csv'):
    """
    Create sample enrollment CSV from JSON curriculum.
    Generates reasonable enrollment numbers based on year levels.
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    program = 'IT'  # From JSON
    
    # Sample enrollment data
    enrollment_data = [
        # 1st year - 40 students per block, 4 blocks
        {'program': program, 'year': 1, 'block': 'A', 'students': 40},
        {'program': program, 'year': 1, 'block': 'B', 'students': 40},
        {'program': program, 'year': 1, 'block': 'C', 'students': 40},
        {'program': program, 'year': 1, 'block': 'D', 'students': 40},
        
        # 2nd year - 40 students per block, 3 blocks
        {'program': program, 'year': 2, 'block': 'A', 'students': 40},
        {'program': program, 'year': 2, 'block': 'B', 'students': 40},
        {'program': program, 'year': 2, 'block': 'C', 'students': 40},
        
        # 3rd year - 35 students per block, 3 blocks
        {'program': program, 'year': 3, 'block': 'A', 'students': 35},
        {'program': program, 'year': 3, 'block': 'B', 'students': 35},
        {'program': program, 'year': 3, 'block': 'C', 'students': 35},
        
        # 4th year - 25 students per block, 2 blocks
        {'program': program, 'year': 4, 'block': 'A', 'students': 25},
        {'program': program, 'year': 4, 'block': 'B', 'students': 25},
    ]
    
    df = pd.DataFrame(enrollment_data)
    df.to_csv(output_file, index=False)
    print(f"✓ Generated enrollment file: {output_file}")
    return df


def main():
    """Example usage and testing."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python json_parser.py <curriculum.json>")
        print("\nExample:")
        print("  python json_parser.py 'all it course.json'")
        return
    
    json_file = sys.argv[1]
    
    print("="*60)
    print("CURRICULUM JSON PARSER")
    print("="*60)
    print(f"\nParsing: {json_file}")
    
    # Parse curriculum
    parser = CurriculumJSONParser(json_file)
    
    # Get summary
    summary = parser.get_summary()
    print("\n📊 Curriculum Summary:")
    print(f"  Total Courses: {summary['total_courses']}")
    print(f"  Total Units: {summary['total_units']}")
    print(f"  Total Lecture Hours: {summary['total_lec_hours']}")
    print(f"  Total Lab Hours: {summary['total_lab_hours']}")
    
    print("\n📚 Courses by Year:")
    for year, count in sorted(summary['courses_by_year'].items()):
        print(f"  Year {year}: {count} courses")
    
    print("\n🏢 Courses by Room Type:")
    for room_type, count in sorted(summary['courses_by_room_type'].items()):
        print(f"  {room_type}: {count} courses")
    
    # Save to CSV
    output_csv = 'courses_from_json.csv'
    courses_df = parser.save_to_csv(output_csv)
    print(f"\n✓ Saved courses to: {output_csv}")
    print(f"  ({len(courses_df)} courses)")
    
    # Create enrollment file
    enrollment_file = 'enrollment_from_json.csv'
    enrollment_df = create_sample_enrollment_from_json(json_file, enrollment_file)
    print(f"\n✓ Generated sample enrollment: {enrollment_file}")
    print(f"  Total students: {enrollment_df['students'].sum()}")
    
    print("\n" + "="*60)
    print("Conversion complete! Files ready for scheduler.")
    print("="*60)


if __name__ == "__main__":
    main()
