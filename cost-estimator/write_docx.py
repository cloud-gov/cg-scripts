import shutil
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches

def insert_rows_into_table(doc_path, table_index, data):
    """
    Inserts rows with data into a specified table in a Word document.

    Args:
        doc_path (str): Path to the Word document.
        table_index (int): Index of the table to modify (0-based).
        data (list of lists): A list of lists, where each inner list represents a row of data.
                           Each element in the inner list is the text for a cell in that row.
    """
    document = Document(doc_path)

    try:
        table = document.tables[table_index]
    except IndexError:
        print(f"Error: Table with index {table_index} not found.")
        return

    for row_data in data:
        row_cells = table.add_row().cells  # Add a new row

        if len(row_data) != len(row_cells):
            print(f"Warning: Data row length ({len(row_data)}) does not match table width ({len(row_cells)}).")
            # You might want to handle this more gracefully (e.g., pad with empty strings)
            # Or skip the row

        for i, cell_text in enumerate(row_data):
            row_cells[i].text = str(cell_text) # Convert to string to handle numbers, etc.

    document.save(doc_path)
    print(f"Table at index {table_index} in '{doc_path}' updated successfully.")

# Example Usage:
if __name__ == '__main__':
    input_document = "Cloud.docx"
    output_document = "Quote.docx"
    shutil.copy(input_document, output_document)
    table_index_to_update = 0  # Index of the table you want to modify

    # Sample data to insert
    new_data = [
        ["Cloud.gov credit estimate for org: dhs-cisa-getgov", "N/A", "105"],
        ["Pages website: www.get.gov|get.gov", "N/A", "12"],
        ["Pages website: beta.get.gov", "N/A", "12"],
        ["Pages website: cyber.dhs.gov", "N/A", "12"]
    ]

    insert_rows_into_table(output_document, table_index_to_update, new_data)