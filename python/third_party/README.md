# Deploy Third Party Agents

## ai-hedge-fund

```bash
# ... install 
cd ./ai-hedge-fund
echo "uv: $(which uv)"
echo "python: $(which python)"

uv run -m adapter --env-file ${path_to_dotenv}
# or simply
bash launch_adapter.sh
```