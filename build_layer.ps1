# Clean old build
Remove-Item -Recurse -Force layer_dir -ErrorAction Ignore
New-Item -ItemType Directory -Path layer_dir/python/lib/python3.10/site-packages -Force | Out-Null

# Install requirements into the correct folder
pip install -r requirements.txt -t layer_dir/python/lib/python3.10/site-packages

# Create the ZIP
Compress-Archive -Path layer_dir/* -DestinationPath layer.zip -Force