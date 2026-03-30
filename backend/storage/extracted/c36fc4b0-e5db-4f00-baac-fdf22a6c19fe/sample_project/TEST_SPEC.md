# Test Specification for Sample Todo API

## Test Case 1: Health Check
**Endpoint:** `GET /health`
**Expected Status:** `200`
**Input:** (empty)
**Expected:** Returns healthy status

## Test Case 2: Get All Todos
**Endpoint:** `GET /todos`
**Expected Status:** `200`
**Input:** (empty)
**Expected:** Returns list of todos

## Test Case 3: Get Specific Todo
**Endpoint:** `GET /todos/1`
**Expected Status:** `200`
**Input:** (empty)
**Expected:** Returns the todo with ID 1

## Test Case 4: Get Non-Existent Todo (Should Fail)
**Endpoint:** `GET /todos/999`
**Expected Status:** `404`
**Input:** (empty)
**Expected:** Returns 404 error

## Test Case 5: Create New Todo
**Endpoint:** `POST /todos`
**Expected Status:** `201`
**Input:** `{"title": "Test Todo", "description": "A test todo item"}`
**Expected:** Returns created todo with ID

## Test Case 6: Update Todo
**Endpoint:** `PUT /todos/1`
**Expected Status:** `200`
**Input:** `{"completed": true}`
**Expected:** Returns updated todo with completed=true

## Test Case 7: Get Statistics
**Endpoint:** `GET /stats`
**Expected Status:** `200`
**Input:** (empty)
**Expected:** Returns statistics about todos

## Test Case 8: Get API Info
**Endpoint:** `GET /info`
**Expected Status:** `200`
**Input:** (empty)
**Expected:** Returns API information and endpoints
