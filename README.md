# Auto-Typesetting
Automating process of typesetting for books, especially in use of Adobe Indesign

Downloading requirements.txt

Putting the original text in docx format, rename the file into 'word' under the folder Auto-Typesetting and change the Indesign template under the template folder.

Running bash code : python main.py --input word.docx --output output.idml --template template/book.idml --config config/style_map.json

It will generate the results in indd format named 'output' in the folder Auto-Typesetting 

The module is still in progress which will connect with AI agent later to help with generating template and recognising context in word.docx automatically
