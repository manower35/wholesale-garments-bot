import os
from PIL import Image

workspace_dir = r"c:\Users\attar\Desktop\Wholesale Readymade Garments"

# Define the image edit operations
# We use patch cloning (copying an adjacent clean background patch and pasting it over the text)
# to keep the texture, lighting, and gradients perfectly natural.
edits = [
    {
        "filename": "kids_frock_484.jpg",
        # Price is at the bottom center: "Rs:484/-"
        # We copy a patch from slightly above and paste it over the text
        "src_box": (380, 840, 740, 890), # (left, top, right, bottom)
        "dest_box": (380, 900, 740, 950)
    },
    {
        "filename": "kids_gown_662.jpg",
        # Price is at the bottom center/right: "Rs:662/-"
        # Copy a patch from slightly above and paste it over the text
        "src_box": (520, 1000, 960, 1050),
        "dest_box": (520, 1070, 960, 1120)
    },
    {
        "filename": "girls_sharara_615.jpg",
        # Price is at the top left below the logo: "Rs:615/-"
        # Copy a patch of wallpaper from slightly above the text and paste it over
        "src_box": (10, 130, 185, 180),
        "dest_box": (10, 190, 185, 240)
    },
    {
        "filename": "girls_sharara_783.jpg",
        # Price is at the top left below the logo: "Rs:783/-"
        "src_box": (10, 130, 185, 180),
        "dest_box": (10, 190, 185, 240)
    },
    {
        "filename": "girls_sharara_purple_783.jpg",
        # Price is at the top left below the logo: "Rs:783/-"
        "src_box": (10, 130, 185, 180),
        "dest_box": (10, 190, 185, 240)
    }
]

def main():
    print("====================================================")
    print("     Removing Price Text Overlays from JPEGs        ")
    print("====================================================")
    
    for edit in edits:
        filepath = os.path.join(workspace_dir, edit["filename"])
        if not os.path.exists(filepath):
            print(f"[-] File not found: {edit['filename']}")
            continue
            
        try:
            img = Image.open(filepath)
            # Copy clean patch
            patch = img.crop(edit["src_box"])
            # Paste over text
            img.paste(patch, edit["dest_box"])
            # Save back
            img.save(filepath, quality=95)
            print(f"[+] Price text removed from: {edit['filename']} (Texture patched)")
        except Exception as e:
            print(f"[-] Failed to edit {edit['filename']}: {e}")
            
    print("====================================================")

if __name__ == "__main__":
    main()
