"""
Elective Configuration Tool
Maps voted electives to placeholder slots based on student preferences
"""

import pandas as pd
import json


class ElectiveConfigurator:
    """Configure which specific electives are offered based on voting."""
    
    def __init__(self, curriculum_json: str):
        """Load curriculum with available electives."""
        with open(curriculum_json, 'r', encoding='utf-8') as f:
            self.curriculum = json.load(f)
        
        self.available_electives = {
            elec['code'].replace(' ', ''): elec 
            for elec in self.curriculum.get('elective_courses', [])
        }
    
    def configure_block_electives(self, program: str, year: int, block: str, 
                                  elective_votes: dict) -> dict:
        """
        Configure which electives a specific block will take.
        
        Args:
            program: Program code (e.g., 'IT')
            year: Year level (3 or 4)
            block: Block letter (A, B, C, etc.)
            elective_votes: Dict mapping elective slots to chosen courses
                Example: {
                    'ITELECT001': 'IT139',  # AI wins vote for slot 1
                    'ITELECT002': 'IT135'   # Game Programming for slot 2
                }
        
        Returns:
            Configuration dict
        """
        config = {
            'program': program,
            'year': year,
            'block': block,
            'electives': {}
        }
        
        for slot, chosen_code in elective_votes.items():
            if chosen_code in self.available_electives:
                elective = self.available_electives[chosen_code]
                config['electives'][slot] = {
                    'placeholder': slot,
                    'actual_course': chosen_code,
                    'name': elective['description'],
                    'lec': elective['lec'],
                    'lab': elective['lab']
                }
            else:
                print(f"Warning: {chosen_code} not found in available electives")
        
        return config
    
    def generate_courses_csv_with_electives(self, base_csv: str, 
                                           elective_configs: list,
                                           output_csv: str):
        """
        Generate courses.csv with specific electives based on voting.
        
        Args:
            base_csv: Base courses CSV from JSON (courses_from_json.csv)
            elective_configs: List of elective configurations from voting
            output_csv: Output CSV file path
        """
        # Load base courses
        df = pd.read_csv(base_csv)
        
        # For each configuration, replace placeholder with actual course
        for config in elective_configs:
            program = config['program']
            year = config['year']
            block = config['block']
            
            for slot, details in config['electives'].items():
                # Find placeholder in base courses for this year
                mask = (df['code'] == slot) & (df['year'] == year)
                
                if mask.any():
                    # Replace placeholder with actual elective
                    df.loc[mask, 'code'] = details['actual_course']
                    df.loc[mask, 'name'] = details['name']
                    df.loc[mask, 'lec_hours'] = details['lec']
                    df.loc[mask, 'lab_hours'] = details['lab']
                else:
                    print(f"Warning: Placeholder {slot} not found for Year {year}")
        
        # Save updated courses
        df.to_csv(output_csv, index=False)
        print(f"✓ Generated courses with electives: {output_csv}")
        return df


def example_usage():
    """Example of configuring electives based on voting."""
    print("="*60)
    print("ELECTIVE CONFIGURATION TOOL")
    print("="*60)
    print()
    
    # Initialize configurator
    config = ElectiveConfigurator('it_curriculum.json')
    
    print("📚 Available Electives:")
    for code, elec in config.available_electives.items():
        print(f"  {code}: {elec['description']}")
    print()
    
    # Example: Configure electives based on voting results
    print("🗳️ Example Voting Results:")
    print()
    
    # Year 3, Block A voting results
    print("IT3A voted for:")
    print("  Slot 1 (ITELECT001): IT139 - Introduction to AI (highest votes)")
    print("  Slot 2 (ITELECT002): IT135 - Game Programming")
    
    config_3a = config.configure_block_electives(
        program='IT',
        year=3,
        block='A',
        elective_votes={
            'ITELECT001': 'IT139',  # AI
            'ITELECT002': 'IT135'   # Game Programming
        }
    )
    
    # Year 3, Block B voting results
    print("\nIT3B voted for:")
    print("  Slot 1 (ITELECT001): IT140 - Data Mining")
    print("  Slot 2 (ITELECT002): IT131 - Web Systems")
    
    config_3b = config.configure_block_electives(
        program='IT',
        year=3,
        block='B',
        elective_votes={
            'ITELECT001': 'IT140',  # Data Mining
            'ITELECT002': 'IT131'   # Web Systems
        }
    )
    
    # Year 4 electives
    print("\nIT4A voted for:")
    print("  Slot 3 (ITELECT003): IT136 - Enterprise Architecture")
    print("  Slot 4 (ITELECT004): IT137 - IT Trends Seminar")
    
    config_4a = config.configure_block_electives(
        program='IT',
        year=4,
        block='A',
        elective_votes={
            'ITELECT003': 'IT136',
            'ITELECT004': 'IT137'
        }
    )
    
    # Generate final courses CSV
    print()
    print("📝 Generating courses.csv with voted electives...")
    
    all_configs = [config_3a, config_3b, config_4a]
    
    df = config.generate_courses_csv_with_electives(
        base_csv='courses_from_json.csv',
        elective_configs=all_configs,
        output_csv='courses_with_electives.csv'
    )
    
    print()
    print("✅ Configuration complete!")
    print(f"   Total courses: {len(df)}")
    print(f"   Ready for scheduler!")
    print()
    print("Next step:")
    print("  Use 'courses_with_electives.csv' in the scheduler GUI")


def interactive_configuration():
    """Interactive mode for configuring electives."""
    print("="*60)
    print("INTERACTIVE ELECTIVE CONFIGURATION")
    print("="*60)
    print()
    
    config = ElectiveConfigurator('it_curriculum.json')
    
    print("Available Electives:")
    electives_list = list(config.available_electives.items())
    for i, (code, elec) in enumerate(electives_list, 1):
        print(f"  {i}. {code}: {elec['description']}")
    print()
    
    # Simple example for one block
    print("Configure electives for IT3A:")
    print()
    
    try:
        # Slot 1
        print("Which elective won the vote for ITELECT001 (slot 1)?")
        choice1 = input("Enter elective code (e.g., IT139): ").strip().upper()
        
        # Slot 2
        print("Which elective won the vote for ITELECT002 (slot 2)?")
        choice2 = input("Enter elective code (e.g., IT135): ").strip().upper()
        
        # Create configuration
        config_3a = config.configure_block_electives(
            program='IT',
            year=3,
            block='A',
            elective_votes={
                'ITELECT001': choice1,
                'ITELECT002': choice2
            }
        )
        
        print()
        print("✓ Configuration saved:")
        print(json.dumps(config_3a, indent=2))
        
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        interactive_configuration()
    else:
        example_usage()
