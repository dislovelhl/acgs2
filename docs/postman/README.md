# ACGS-2 API Documentation & Testing

This directory contains Postman collections and documentation for testing ACGS-2 APIs.

## 📋 Collections

### ACGS2_API_Collection.postman_collection.json
Complete API collection covering all ACGS-2 services and endpoints.

## 🚀 Quick Start

1. **Import Collection**
   - Open Postman
   - Click "Import" button
   - Select "File"
   - Choose `ACGS2_API_Collection.postman_collection.json`

2. **Configure Environment**
   - Create a new environment in Postman
   - Set the following variables:
     ```
     base_url: http://localhost:8080
     agent_bus_url: http://localhost:8000
     opa_url: http://localhost:8181
     tenant_id: acgs-dev
     ```

3. **Start Development Environment**
   ```bash
   cd /path/to/acgs2
   ./scripts/start-dev.sh
   ```

4. **Run Tests**
   - Start with "Health Checks" folder to verify services are running
   - Test basic functionality with "Agent Bus API" requests
   - Use "Load Testing" for performance validation

## 📚 API Endpoints

### API Gateway (Port 8080)
- `GET /health` - Gateway health check
- `GET /services` - List available services
- `POST /messages` - Proxy message to Agent Bus

### Agent Bus (Port 8000)
- `GET /health` - Agent Bus health check
- `POST /messages` - Send message to processing pipeline
- `GET /messages/{id}` - Get message status
- `GET /stats` - Get processing statistics
- `POST /policies/validate` - Validate policy compliance

### Open Policy Agent (Port 8181)
- `GET /health` - OPA health check
- `POST /v1/data/{policy}` - Query policies

## 🧪 Test Scenarios

### Basic Functionality
1. Health checks for all services
2. Send simple user request message
3. Verify message processing

### Advanced Scenarios
1. High-priority system alerts
2. Policy updates and validation
3. Load testing with multiple concurrent requests

### Error Handling
1. Invalid message formats
2. Missing required fields
3. Non-existent endpoints

## 🔧 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `base_url` | `http://localhost:8080` | API Gateway URL |
| `agent_bus_url` | `http://localhost:8000` | Agent Bus direct URL |
| `opa_url` | `http://localhost:8181` | OPA policy engine URL |
| `tenant_id` | `acgs-dev` | Tenant identifier for multi-tenancy |

## 📊 Monitoring & Debugging

### Response Validation
All requests include test scripts to validate:
- HTTP status codes
- Response schemas
- Required fields presence
- Error message formats

### Performance Testing
Use Postman's Runner feature with the "Load Testing" folder to:
- Test concurrent request handling
- Measure response times
- Identify performance bottlenecks

### Logging
Check service logs for detailed request/response information:
```bash
# View all service logs
docker-compose -f docker-compose.dev.yml logs -f

# View specific service logs
docker-compose -f docker-compose.dev.yml logs -f agent-bus
```

## 🐛 Troubleshooting

### Common Issues

**Connection Refused**
- Ensure development environment is running: `./scripts/start-dev.sh`
- Check service health: Visit health endpoints directly

**Service Unavailable (503)**
- Agent Bus may not be fully initialized
- Check logs: `docker-compose -f docker-compose.dev.yml logs agent-bus`

**Validation Errors**
- Review request body format
- Check required fields are present
- Verify tenant_id is set correctly

### Getting Help
- Check the main [CONTRIBUTING.md](../CONTRIBUTING.md) for development setup
- Review service documentation in `docs/` directory
- Create an issue for bugs or unexpected behavior

## 📈 Best Practices

### Testing Strategy
1. Always start with health checks
2. Test individual endpoints before complex scenarios
3. Use environment variables for dynamic configuration
4. Validate responses programmatically where possible

### Performance Testing
1. Start with low concurrency (1-5 requests)
2. Gradually increase load while monitoring response times
3. Test both success and error scenarios
4. Monitor system resources during testing

### API Design Validation
1. Test all CRUD operations
2. Validate error responses match expected schemas
3. Test boundary conditions and edge cases
4. Verify authentication and authorization

## 🔄 CI/CD Integration

This collection can be integrated with:
- Postman Monitors for continuous API testing
- Newman for command-line execution
- GitHub Actions for automated testing
- Performance regression detection

Example GitHub Action:
```yaml
- name: Run API Tests
  run: |
    npm install -g newman
    newman run docs/postman/ACGS2_API_Collection.postman_collection.json \
      --environment docs/postman/ACGS2_Dev_Environment.postman_environment.json
```
