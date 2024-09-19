import yaml
import httpx
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()

# OAuth2 Authentication (Basic implementation for demo purposes)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Role-based access control (for demonstration purposes)
roles = {
    "user": {"permissions": ["ocr", "ner"]},
    "admin": {"permissions": ["ocr", "ner", "config"]},
}

# Load the configuration from YAML
def load_config(file_path='config.yaml'):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()

# Fetch OpenAPI specifications dynamically from the given URLs
async def fetch_openapi(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{url}/openapi.json")
        response.raise_for_status()
        return response.json()

# Route for role validation (basic token-based user validation)
def get_current_user(token: str = Depends(oauth2_scheme)):
    # Simple mock authentication
    if token == "admin_token":
        return {"username": "admin", "role": "admin"}
    elif token == "user_token":
        return {"username": "user", "role": "user"}
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

# Create routes dynamically based on the configuration
@app.on_event("startup")
async def create_dynamic_routes():
    for endpoint in config['endpoints']:
        openapi_spec = await fetch_openapi(endpoint['url'])

        @app.api_route(f"/{endpoint['prefix']}", methods=["GET", "POST", "PUT", "DELETE"])
        async def proxy_to_service(request: Request, current_user: dict = Depends(get_current_user)):
            # Check permission for the current user role
            if endpoint['name'] not in roles[current_user['role']]['permissions']:
                raise HTTPException(status_code=403, detail="Permission denied")

            # Forward the request to the microservice
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=request.method,
                    url=f"{endpoint['url']}{request.url.path}",
                    headers=request.headers,
                    content=await request.body()
                )
                return response.json()

# Basic route to test the API
@app.get("/")
async def read_root():
    return {"message": "Welcome to the API Manager!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
