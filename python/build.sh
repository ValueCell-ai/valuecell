# uv build

# macOS
# uvx pex -v \
#     --venv-repository ./.venv \
#     -e valuecell.server.main:main \
#     -o dist/valuecell.pex \
#     --scie eager \
#     --scie-pbs-stripped

# Windows
# -r dist/requirements.txt \

# uvx pex dist/valuecell-0.1.4-py3-none-any.whl \
#     -e valuecell.server.main:main \
#     -o dist/valuecell \
#     --scie eager \
#     --scie-pbs-stripped \
#     --platform=win_amd64-cp-3.12.11-cp312 \
#     -v

# pyinstaller --onefile --name=valuecell --paths=. valuecell/server/main.py