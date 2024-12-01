from pymongo import MongoClient

# Connect to MongoDB server
def get_database():
    """Establish a connection to the MongoDB database."""
    client = MongoClient("mongodb://localhost:27017/")  # Update with your MongoDB URI if hosted elsewhere
    return client["foundersuite"]  # Name of the database

# Insert data into the 'firms' collection only if it doesn't already exist
def insert_firm(data):
    """
    Inserts a document into the 'firms' collection if it doesn't already exist.

    Parameters:
    data (dict): The data to insert. Example: {"name": "TechFirm", "location": "San Francisco"}

    Returns:
    str: Message indicating whether the data was inserted or already exists.
    """
    db = get_database()
    firms_collection = db["firms"]

    # Check if a document with the same name exists
    if firms_collection.find_one({"name": data.get("name")}):
        return "Firm already exists."

    # Insert if not found
    result = firms_collection.insert_one(data)
    return f"Inserted firm with ID: {result.inserted_id}"

# Insert data into the 'slug' collection only if it doesn't already exist
def insert_slug(data):
    """
    Inserts a document into the 'slug' collection if it doesn't already exist.

    Parameters:
    data (dict): The data to insert. Example: {"slug": "techfirm", "type": "company"}

    Returns:
    str: Message indicating whether the data was inserted or already exists.
    """
    db = get_database()
    slug_collection = db["slug"]

    # Check if a document with the same slug exists
    if slug_collection.find_one({"current_page": data.get("current_page")}):
        return "Slug already exists."

    # Insert if not found
    result = slug_collection.insert_one(data)
    return f"Inserted slug with ID: {result.inserted_id}"

# Example Usage (Comment these out if not using immediately)
# firm_data = {"name": "TechFirm", "location": "San Francisco", "industry": "Technology"}
# slug_data = {"slug": "techfirm", "type": "company"}

# print(insert_firm(firm_data))
# print(insert_slug(slug_data))
