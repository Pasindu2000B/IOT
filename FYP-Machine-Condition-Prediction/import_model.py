"""
Model Import Tool - Import trained models from various sources

This tool helps you import already-trained PatchTST models into the inference system.

Supported sources:
1. Local file system (another folder/drive)
2. Google Drive (download link)
3. URL (direct download)
4. Network path
"""

import os
import sys
import shutil
import requests
from pathlib import Path
from datetime import datetime

class ModelImporter:
    def __init__(self):
        self.base_dir = Path(__file__).parent / "FYP-Machine-Condition-Prediction"
        self.base_dir.mkdir(exist_ok=True)
        
    def import_from_local(self, model_path, scaler_path, workspace_id=None):
        """
        Import model from local file system
        
        Args:
            model_path: Path to model folder
            scaler_path: Path to scaler .pkl file
            workspace_id: Optional workspace ID (auto-detected if not provided)
        """
        model_path = Path(model_path)
        scaler_path = Path(scaler_path)
        
        # Validate files exist
        if not model_path.exists():
            return {"status": "error", "message": f"Model path not found: {model_path}"}
        if not scaler_path.exists():
            return {"status": "error", "message": f"Scaler path not found: {scaler_path}"}
        
        # Auto-detect workspace_id from folder name if not provided
        if workspace_id is None:
            dir_name = model_path.name
            if dir_name.startswith("model_"):
                parts = dir_name.replace("model_", "").split("_")
                if len(parts) >= 3:
                    workspace_id = "_".join(parts[:-2])
                else:
                    workspace_id = dir_name.replace("model_", "")
            else:
                return {"status": "error", "message": "Cannot detect workspace_id. Please provide it manually."}
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Target names
        target_model_dir = self.base_dir / f"model_{workspace_id}_{timestamp}"
        target_scaler_file = self.base_dir / f"scaler_{workspace_id}_{timestamp}.pkl"
        
        print(f"\n📦 Importing model for workspace: {workspace_id}")
        print(f"   Source model: {model_path}")
        print(f"   Source scaler: {scaler_path}")
        print(f"   Target location: {self.base_dir}")
        
        # Copy model directory
        try:
            if target_model_dir.exists():
                print(f"   ⚠️  Removing existing model...")
                shutil.rmtree(target_model_dir)
            
            shutil.copytree(model_path, target_model_dir)
            print(f"   ✅ Model folder copied")
            
            # Copy scaler
            shutil.copy2(scaler_path, target_scaler_file)
            print(f"   ✅ Scaler file copied")
            
            # Verify required files
            required_files = ['config.json', 'pytorch_model.bin']
            missing_files = []
            for file in required_files:
                if not (target_model_dir / file).exists():
                    missing_files.append(file)
            
            if missing_files:
                return {
                    "status": "error",
                    "message": f"Missing required files: {', '.join(missing_files)}"
                }
            
            print(f"\n✅ Import successful!")
            print(f"\n📋 Model details:")
            print(f"   Workspace ID: {workspace_id}")
            print(f"   Model folder: {target_model_dir.name}")
            print(f"   Scaler file: {target_scaler_file.name}")
            print(f"\n🚀 Next steps:")
            print(f"   1. Restart inference server: python main.py")
            print(f"   2. Verify model loaded in logs")
            print(f"   3. Check dashboard: http://localhost:8000")
            
            return {
                "status": "success",
                "workspace_id": workspace_id,
                "model_dir": str(target_model_dir),
                "scaler_file": str(target_scaler_file)
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Import failed: {str(e)}"}
    
    def import_from_url(self, model_url, scaler_url, workspace_id):
        """
        Download model from URL (e.g., Google Drive, Dropbox, or direct link)
        
        Args:
            model_url: URL to model zip file
            scaler_url: URL to scaler .pkl file
            workspace_id: Workspace identifier
        """
        import tempfile
        import zipfile
        
        print(f"\n📥 Downloading model from URL...")
        print(f"   Workspace ID: {workspace_id}")
        
        try:
            # Create temp directory
            temp_dir = Path(tempfile.mkdtemp())
            
            # Download model zip
            print(f"\n   Downloading model...")
            model_zip_path = temp_dir / "model.zip"
            response = requests.get(model_url, stream=True)
            response.raise_for_status()
            
            with open(model_zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"   ✅ Model downloaded")
            
            # Extract model
            print(f"   Extracting model...")
            model_extract_dir = temp_dir / "model_extracted"
            with zipfile.ZipFile(model_zip_path, 'r') as zip_ref:
                zip_ref.extractall(model_extract_dir)
            
            # Find model folder (first directory in extracted files)
            model_folders = [d for d in model_extract_dir.iterdir() if d.is_dir()]
            if not model_folders:
                return {"status": "error", "message": "No model folder found in zip"}
            model_folder = model_folders[0]
            print(f"   ✅ Model extracted")
            
            # Download scaler
            print(f"\n   Downloading scaler...")
            scaler_path = temp_dir / "scaler.pkl"
            response = requests.get(scaler_url)
            response.raise_for_status()
            
            with open(scaler_path, 'wb') as f:
                f.write(response.content)
            print(f"   ✅ Scaler downloaded")
            
            # Import using local import method
            result = self.import_from_local(model_folder, scaler_path, workspace_id)
            
            # Cleanup temp files
            shutil.rmtree(temp_dir)
            
            return result
            
        except Exception as e:
            return {"status": "error", "message": f"Download failed: {str(e)}"}
    
    def list_installed_models(self):
        """List all currently installed models"""
        model_dirs = sorted(self.base_dir.glob("model_*"))
        
        if not model_dirs:
            print("\n📦 No models installed")
            return []
        
        print(f"\n📦 Installed models ({len(model_dirs)}):")
        models = []
        
        for model_dir in model_dirs:
            # Extract workspace_id
            dir_name = model_dir.name
            parts = dir_name.replace("model_", "").split("_")
            if len(parts) >= 3:
                workspace_id = "_".join(parts[:-2])
                timestamp = "_".join(parts[-2:])
            else:
                workspace_id = dir_name.replace("model_", "")
                timestamp = "unknown"
            
            # Check for scaler
            scaler_pattern = f"scaler_{workspace_id}_*.pkl"
            scaler_files = list(self.base_dir.glob(scaler_pattern))
            has_scaler = len(scaler_files) > 0
            
            models.append({
                "workspace_id": workspace_id,
                "folder": model_dir.name,
                "timestamp": timestamp,
                "has_scaler": has_scaler
            })
            
            status = "✅" if has_scaler else "⚠️ (missing scaler)"
            print(f"   {status} {workspace_id}")
            print(f"      Folder: {model_dir.name}")
        
        return models


def main():
    """Interactive CLI for model import"""
    importer = ModelImporter()
    
    print("=" * 70)
    print("  MODEL IMPORT TOOL - Import Trained Models to Inference System")
    print("=" * 70)
    
    while True:
        print("\n📋 Options:")
        print("   1. Import from local file system")
        print("   2. Import from URL (Google Drive, Dropbox, etc.)")
        print("   3. List installed models")
        print("   4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            # Local import
            print("\n" + "=" * 70)
            print("  IMPORT FROM LOCAL FILE SYSTEM")
            print("=" * 70)
            
            model_path = input("\nModel folder path: ").strip().strip('"')
            scaler_path = input("Scaler file path: ").strip().strip('"')
            
            use_custom_id = input("\nUse custom workspace ID? (y/n): ").lower()
            workspace_id = None
            if use_custom_id == 'y':
                workspace_id = input("Enter workspace ID: ").strip()
            
            result = importer.import_from_local(model_path, scaler_path, workspace_id)
            
            if result["status"] == "error":
                print(f"\n❌ Error: {result['message']}")
            
        elif choice == "2":
            # URL import
            print("\n" + "=" * 70)
            print("  IMPORT FROM URL")
            print("=" * 70)
            print("\n💡 Tip: For Google Drive, use the direct download link")
            print("   Format: https://drive.google.com/uc?export=download&id=FILE_ID")
            
            model_url = input("\nModel zip URL: ").strip()
            scaler_url = input("Scaler file URL: ").strip()
            workspace_id = input("Workspace ID: ").strip()
            
            result = importer.import_from_url(model_url, scaler_url, workspace_id)
            
            if result["status"] == "error":
                print(f"\n❌ Error: {result['message']}")
        
        elif choice == "3":
            # List models
            importer.list_installed_models()
        
        elif choice == "4":
            print("\n👋 Exiting...")
            break
        
        else:
            print("\n❌ Invalid option. Please try again.")


if __name__ == "__main__":
    # Check if command line arguments provided
    if len(sys.argv) >= 3:
        # Command line mode
        importer = ModelImporter()
        model_path = sys.argv[1]
        scaler_path = sys.argv[2]
        workspace_id = sys.argv[3] if len(sys.argv) > 3 else None
        
        result = importer.import_from_local(model_path, scaler_path, workspace_id)
        
        if result["status"] == "error":
            print(f"\n❌ Error: {result['message']}")
            sys.exit(1)
    else:
        # Interactive mode
        main()
