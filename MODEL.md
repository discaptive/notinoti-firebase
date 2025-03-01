## Cloud Firestore Data model

```markdown
settings  # collection
  - general  # document
    - welcome  # field (string)
    - support  # field (string)
    - version  # field (string)
    - startDay  # field (timestamp)
    - lastDay  # field (timestamp)
  - processing_flag  # document
    - status  # field (boolean)
    
popular-notices  # collection
  - popular-notice-doc-id  # document
    - title  # field (string)
    - author  # field (string)
    - hits  # field (number)
    - link  # field (string)
    - createdAt  # field (timestamp)
    - isFixed  # field (boolean)
    - score  # field (number)
    
new-notices  # collection
  - new-notice-doc-id  # document
    - title  # field (string)
    - description  # field(string)
    - link  # field (string)
    - pubDate  # field (timestamp)
    
announcements  # collection
  - announcement-doc-id  # document
    - title  # field (string)
    - content  # field (string)
    - createdAt  # field (timestamp)
    - notification  # field (boolean)
    
collaborative-calendars  # collection
  - collaborative-calendar-doc-id  # document
    - title  # field (string)
    - startDay  # field (timestamp)
    - lastDay  # field (timestamp)
    - link  # field (string)
    - memo  # field (string)
    - createdAt  # field (timestamp)
    - author  # field (string)
    - notification  # field (boolean)
    - color  # field (string)
    
new-foods  # collection
  - new-food-doc-id  # document
    - name  # field (string)
    - togo  # field (boolean)
    - price  # field (number)
    - type  # field (string)
    
users  # collection
  - user-doc-id  # document
    - deviceToken  # field (string)
    - createdAt  # field (timestamp)
    - lastActive  # field (timestamp)
    - role  # field (string)
    - notifications  # field (string[])
    - keywords  # field (string[])
    
keywords  # collection
  - keyword-doc-id  # document
    - keyword  # field (string)
    - subscribers  # field (string[])
```
