
You can use the queries in Neo4j Query window.

## 1.  Paths

* Find all paths

```
MATCH p = (n:User)-[*1..5]->(m:Group {name:'DOMAIN ADMINS@ECORP.NICODOMAIN.PRV'})
WHERE NOT n = m
RETURN p
```
* Shortest path from users

```

MATCH p = shortestPath(
    (n:User)-[*1..]->(m:Group)
)
WHERE m.name IN ['MTREOLA00092@TESTLAB.LOCALE', 'ENTERPRISE ADMINS@ECORP.NICODOMAIN.PRV']
AND NOT n = m
RETURN p

```

```

MATCH p=shortestPath((n:User)-[*1..]->(m:Group {name: 'DOMAIN ADMINS@ECORP.NICODOMAIN.PRV'}))
WHERE NOT n=m RETURN p

```

* Shortest path from user to group

```
MATCH (u:User {name:'RKANOFF00169@TESTLAB.LOCALE'}),
      (g:Group {name:'DOMAIN ADMINS@TESTLAB.LOCALE'})
MATCH p = shortestPath((u)-[*1..]->(g))
RETURN p;


MATCH (u:User {name:"STERAN00257@TESTLAB.LOCALE"}),
      (g:Group {name:'DOMAIN ADMINS@TESTLAB.LOCALE'})
MATCH p = shortestPath((u)-[*1..]->(g))
RETURN p;

```

* Fetch all shortest paths

```
MATCH p = shortestPath(
  (u:User)-[*1..]->(g:Group {name:'DOMAIN ADMINS@TESTLAB.LOCALE'})
)
WHERE NOT u = g
RETURN p;
```

```
<!-- Path with nodes and length -->
MATCH p = shortestPath(
  (u:User)-[*1..]->(g:Group {name: 'DOMAIN ADMINS@TESTLAB.LOCALE'})
)
WHERE u <> g
RETURN length(p) AS pathLength,
       nodes(p)  AS pathNodes;

```

* Shortest path to domain admin users

```
MATCH (g:Group {name:'DOMAIN ADMINS@TESTLAB.LOCALE'})
CALL apoc.path.subgraphAll(g, {
  maxLevel: 5,
  relationshipFilter: ">",
  labelFilter: "+User|+Group"
})
YIELD nodes, relationships
RETURN nodes, relationships;

```

* Shortest path from specific user

```
MATCH (u:User {name:'MHOLLENBAUGH00339@TESTLAB.LOCALE'}),
      (g:Group {name:'DOMAIN ADMINS@TESTLAB.LOCALE'})
MATCH p = shortestPath((u)-[*1..]->(g))
RETURN p;
```


* Path from computer
```
MATCH (u:Computer {name:'WS-00070@TESTLAB.LOCALE'}),
      (g:Group {name:'DOMAIN ADMINS@TESTLAB.LOCALE'})
MATCH p = shortestPath((u)-[*1..]->(g))
RETURN p;
```




## 2. User queries

* Fetch user 
```
MATCH p = (u:User {name:'RKANOFF00169@TESTLAB.LOCALE'})
RETURN p;

```

* Find user with session

```
MATCH p = (u:User {name:'SLAVELLI00015@TESTLAB.LOCALE'})-[:HasSession]->(c:Computer)
RETURN p;
```


* Find user with session in computer

```
MATCH p = (u:User {name:'LCLYMAN00017@TESTLAB.LOCALE'})-[:HasSession]->(c:Computer) RETURN p

MATCH p = (u:User {name:'RKANOFF00169@TESTLAB.LOCALE'})-[:HasSession]->(c:Computer) RETURN p
```

* List all reachable users

```

 MATCH (u:User), (g:Group {name: "DOMAIN ADMINS@TESTLAB.LOCALE"})
WHERE (u)-[*1..]->(g)
RETURN u.name AS user, g.name AS target;

```


## 3. Computer queries 

* Match Server

```
MATCH p = (c:Computer {name:'S-00012@TESTLAB.LOCALE'})
RETURN p;
```


```
MATCH p = (c:Computer {neo4jImportId:'871'})
RETURN p;
```

* Find computer

```
MATCH p = (c:Computer {name:'WS-00070@TESTLAB.LOCALE'})
RETURN p;
```
* Find computer and user from Session data


```

WITH 'S-00022@TESTLAB.LOCALE->JWHETSEL00060@TESTLAB.LOCALE' AS pair
WITH split(pair, '->') AS parts
WITH parts[0] AS compName, parts[1] AS userName


MATCH (c:Computer {name: compName})
OPTIONAL MATCH (c)-[r1]-(n1)
WITH c, collect(r1) AS compRels, collect(n1) AS compNeighbors, userName

MATCH (u:User {name: userName})
OPTIONAL MATCH (u)-[r2]-(n2)
RETURN 
  c, compRels, compNeighbors,
  u, collect(r2) AS userRels, collect(n2) AS userNeighbors;

```

## 4. Group  queries

* List all groups
MATCH (g:Group)
RETURN g.name AS GroupName
ORDER BY g.name;

* Group membership
```
MATCH (g:Group)
OPTIONAL MATCH (m)-[:MemberOf]->(g)
RETURN 
  g.name AS GroupName, 
  count(m) AS MemberCount,
ORDER BY MemberCount DESC;

```
* Nested group 

```
MATCH (g:Group)
OPTIONAL MATCH (sub:Group)-[:MemberOf]->(g)
RETURN 
  g.name AS ParentGroup,
  collect(DISTINCT sub.name) AS SubGroups
ORDER BY ParentGroup;

```

* Path from user (Direction agnostic)

```
MATCH (u:User {name: "JWHETSEL00060@TESTLAB.LOCALE"}),
      (da:Group {name: "DOMAIN ADMINS@TESTLAB.LOCALE"})
MATCH p = allShortestPaths((u)-[:MemberOf*1..6]-(da))
RETURN 
  p,
  [n IN nodes(p) | {name: n.name, label: labels(n)[0]}] AS PathNodes,
  length(p) AS Hops
ORDER BY Hops ASC




```
* Path from group 

```
// GRP
// MATCH (u:User {name: "BCHEVIS00065@TESTLAB.LOCALE"}),
MATCH (u:Group {name: "T1 PAW Maintenance@TESTLAB.LOCALE"}),
      (da:Group {name: "DOMAIN ADMINS@TESTLAB.LOCALE"})
MATCH p = allShortestPaths((u)-[:MemberOf*1..6]-(da))
RETURN 
  p,
  [n IN nodes(p) | {name: n.name, label: labels(n)[0]}] AS PathNodes,
  length(p) AS Hops
ORDER BY Hops ASC

```
* Path from computer ()
```
MATCH (c:Computer {name: "S-00022@TESTLAB.LOCALE"}),
      (da:Group {name: "DOMAIN ADMINS@TESTLAB.LOCALE"})
MATCH p = allShortestPaths((c)-[*..6]-(da))
RETURN 
  p,
  [n IN nodes(p) | {name: n.name, label: labels(n)[0]}] AS PathNodes,
  length(p) AS Hops
ORDER BY Hops ASC;
```
* Check if path to DA in session

```
WITH 
'PAW-00032@TESTLAB.LOCALE → EZANDERIGO00155@TESTLAB.LOCALE' AS pair
WITH split(pair, ' → ') AS parts
WITH trim(parts[0]) AS compName, trim(parts[1]) AS userName

// ─── Computer neighborhood ───────────────────────────────
MATCH (c:Computer {name: compName})
OPTIONAL MATCH (c)-[r1]-(n1)
WITH c, collect(DISTINCT r1) AS compRels, collect(DISTINCT n1) AS compNeighbors, userName

// ─── User neighborhood ───────────────────────────────────
MATCH (u:User {name: userName})
OPTIONAL MATCH (u)-[r2]-(n2)
WITH c, compRels, compNeighbors, u, collect(DISTINCT r2) AS userRels, collect(DISTINCT n2) AS userNeighbors

// ─── Find path from user to Domain Admins ────────────────
OPTIONAL MATCH pathToDA = allShortestPaths((u)-[:MemberOf*1..6]->(da:Group {name: "DOMAIN ADMINS@TESTLAB.LOCALE"}))
WITH 
  c, compRels, compNeighbors, 
  u, userRels, userNeighbors,
  pathToDA,
  CASE 
    WHEN pathToDA IS NULL THEN false 
    ELSE true 
  END AS hasPathToDA,
  [n IN nodes(pathToDA) | n.name] AS pathNodes

RETURN 
  c.name AS Computer,
  [x IN compNeighbors | x.name] AS ComputerNeighbors,
  u.name AS User,
  [x IN userNeighbors | x.name] AS UserNeighbors,
  hasPathToDA,
  pathNodes

```
* Path with hops

```
MATCH path = (u:User)-[:MemberOf*1..6]->(da:Group {name: 'DOMAIN ADMINS@TESTLAB.LOCALE'})
RETURN 
  u.name AS UserName,
  length(path) AS HopsToDomainAdmins,
  [n IN nodes(path) | n.name] AS PathNodes
ORDER BY HopsToDomainAdmins, UserName;
```
---
# 5. Reset 

* Delete all
```
  MATCH (n)
    DETACH DELETE n
```