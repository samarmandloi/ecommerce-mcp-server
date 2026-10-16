import os
import psycopg

print("PostgreSQL connection successful! hb")

connection = psycopg.connect(
    host=os.environ["PRODUCT_DB_HOST"],
    port=os.environ["PRODUCT_DB_PORT"],
    dbname=os.environ["PRODUCT_DB_NAME"],
    user=os.environ["PRODUCT_DB_USER"],
    password=os.environ["PRODUCT_DB_PASSWORD"],
)

print("PostgreSQL connection successful!")

connection.close()