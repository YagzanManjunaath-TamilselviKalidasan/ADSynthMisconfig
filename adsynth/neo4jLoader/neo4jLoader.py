from neo4j import GraphDatabase

# Replace with your connection info
uri = "bolt://localhost:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "admin123"))
query = """
CALL apoc.load.json("file:///person.json")
YIELD value
RETURN value
LIMIT 5
"""
def run_query(query, params=None):
    with driver.session() as session:
        return session.run(query, params or {})
        
results = run_query(query)

for record in results:
    print(record["value"])



