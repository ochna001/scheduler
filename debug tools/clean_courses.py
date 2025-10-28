import pandas as pd

# Read courses
df = pd.read_csv('courses_from_json.csv')

# Remove IT128 Practicum (shouldn't be in classroom schedule)
df_cleaned = df[df['code'] != 'IT128']

# Save cleaned version
df_cleaned.to_csv('courses_cleaned.csv', index=False)

print(f"✓ Removed IT128 Practicum")
print(f"✓ Courses: {len(df)} → {len(df_cleaned)}")
print(f"✓ Saved to: courses_cleaned.csv")
