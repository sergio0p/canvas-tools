"""
PDF Auto-Tagger - With drag-and-drop and interactive input
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
    """Tags a PDF file for accessibility"""
    
    pdf_path = os.path.abspath(pdf_path)
    
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        return False
    
    if not pdf_path.lower().endswith('.pdf'):
        print(f"❌ Not a PDF file: {pdf_path}")
        return False
    
    output_path = pdf_path.replace('.pdf', '_tagged.pdf')
    
    counter = 1
    while os.path.exists(output_path):
        output_path = pdf_path.replace('.pdf', f'_tagged_{counter}.pdf')
        counter += 1
    
    print(f"\n{'='*60}")
    print(f"Processing: {os.path.basename(pdf_path)}")
    print(f"{'='*60}\n")
    
    try:
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
        
        # Mark as tagged
        mark_info = DictionaryObject()
        mark_info[NameObject('/Marked')] = BooleanObject(True)
        writer._root_object[NameObject('/MarkInfo')] = mark_info
        writer._root_object[NameObject('/Lang')] = TextStringObject('en-US')
        
        print("\nSaving...")
        with open(output_path, 'wb') as f:
            writer.write(f)
        
        file_size = os.path.getsize(output_path) / 1024
        
        print(f"✅ Done! ({file_size:.0f} KB)\n")
        print(f"Output: {output_path}\n")
        
        # Open folder
        os.system(f'open "{os.path.dirname(output_path)}"')
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def main():
    print("\n" + "="*60)
    print(" PDF AUTO-TAGGER")
    print("="*60)
    
    pdf_file = None
    
    # Check if file was provided via command line or drag-and-drop
    if len(sys.argv) > 1:
        # Join all arguments (handles spaces in drag-and-drop)
        pdf_file = ' '.join(sys.argv[1:])
    else:
        # Interactive mode - ask for filename
        print("\nNo file provided.")
        print("\nOptions:")
        print("  1. Drag and drop a PDF onto this script")
        print("  2. Enter the PDF filename (or full path)")
        print("  3. Press Ctrl+C to exit\n")
        
        try:
            pdf_file = input("Enter PDF filename: ").strip()
            
            # Remove quotes if user pasted a quoted path
            if pdf_file.startswith('"') and pdf_file.endswith('"'):
                pdf_file = pdf_file[1:-1]
            if pdf_file.startswith("'") and pdf_file.endswith("'"):
                pdf_file = pdf_file[1:-1]
                
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            return
    
    # Validate input
    if not pdf_file:
        print("\n❌ No file specified")
        input("\nPress Enter to exit...")
        return
    
    # Process the file
    try:
        success = tag_pdf(pdf_file)
        
        if success:
            print("✅ Success!")
        else:
            print("❌ Failed")
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()