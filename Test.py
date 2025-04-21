from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017/")
db = client["mqtt_database"]
sensors_collection = db["your_collection"]

# Получить первый документ
document = sensors_collection.find_one()
print(document)