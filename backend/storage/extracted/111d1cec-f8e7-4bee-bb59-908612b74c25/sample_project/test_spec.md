# Sample API Test Specification

### Health endpoint returns 200
**Endpoint**: GET /health
**Expected**: 200

### Get existing item (id=1)
**Endpoint**: GET /items/1
**Expected**: 200

### Get missing item (404)
**Endpoint**: GET /items/999
**Expected**: 404

### Create new item
**Endpoint**: POST /items
**Input**: {"id": 3, "name": "NewItem", "description": "Created via test"}
**Expected**: 200
