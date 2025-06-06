from dump_MKG_API import dump_pages

from extract_data import extract_from_pages

import os

if not os.path.isdir("./dumps/pages"):
    dump_pages()

extract_from_pages()

