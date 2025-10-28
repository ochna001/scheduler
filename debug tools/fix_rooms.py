import pandas as pd

# Load rooms
rooms_df = pd.read_csv('room_final.csv')

# All these rooms are computer labs, so they should be 'lab' category
rooms_df['room_category'] = 'lab'

# Save the updated file
rooms_df.to_csv('room_final.csv', index=False)
print("Updated room_final.csv with room_category='lab' for all rooms")
print(rooms_df.head())
