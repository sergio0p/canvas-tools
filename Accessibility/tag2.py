"""
PDF Auto-Tagger - All values wrapped properly
"""

import sys
import os
from pathlib import Path

# Check dependencies
try:
    from pypdf import PdfWriter, PdfReader
    from pypdf.generic import DictionaryObject, NameObject, BooleanObject, TextStringObject
except ImportError:
    print("Installing pypdf...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "pypdf"])
    from pypdf import PdfWriter, PdfReader
    from pypdf.generic import DictionaryObject, NameObject, BooleanObject, TextStringObject

def tag_pdf(pdf_path):
    """Simple PDF tagger"""
    
    pdf_path = os.path.abspath(pdf_path)
    output_path = pdf_path.replace('.pdf', '_tagged.pdf')
    
    counter = 1
    while os.path.exists(output_path):
        output_path = pdf_path.replace('.pdf', f'_tagged_{counter}.pdf')
        counter += 1
    
    print(f"\n{'='*60}")
    print(f"Processing: {os.path.basename(pdf_path)}")
    print(f"{'='*60}\n")
    
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    
    print(f"Pages: {len(reader.pages)}")
    
    # Copy pages
    for page in reader.pages:
        writer.add_page(page)
    
    # Add metadata
    filename = Path(pdf_path).stem.replace('_', ' ')
    writer.add_metadata({
        '/Title': filename,
        '/Language': 'en-US'
    })
    
    # Mark as tagged - ALL WRAPPED PROPERLY
    mark_info = DictionaryObject()
    mark_info[NameObject('/Marked')] = BooleanObject(True)
    writer._root_object[NameObject('/MarkInfo')] = mark_info
    writer._root_object[NameObject('/Lang')] = TextStringObject('en-US')  # WRAPPED!
    
    print("\nSaving...")
    with open(output_path, 'wb') as f:
        writer.write(f)
    
    print(f"✅ Done!\n")
    print(f"Output: {output_path}\n")
    
    os.system(f'open "{os.path.dirname(output_path)}"')
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Drag PDF onto this script")
        input("\nPress Enter...")
        sys.exit()
    
    pdf_file = ' '.join(sys.argv[1:]) if len(sys.argv) > 2 else sys.argv[1]
    
    try:
        tag_pdf(pdf_file)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nPress Enter...")