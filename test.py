from pymongo import MongoClient

# Connect to the MongoDB server
client = MongoClient('mongodb+srv://pydevil:B0Qos3zYDIYfoVyp@capitalreachai.1d0li.mongodb.net/?retryWrites=true&w=majority&appName=CapitalReachAI')  # Adjust the connection string as needed

# Access the database and collection
db = client['foundersuite_data']
collection = db['investor_data']

# Define the filter for pages between 1833 and 1861
filter_query = {'Page': {'$gte': 1833, '$lte': 1867}}

# Delete the documents matching the filter
result = collection.delete_many(filter_query)

# Output the result
print(f"Deleted {result.deleted_count} documents.")
