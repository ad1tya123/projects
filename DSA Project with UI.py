import tkinter as tk
from tkinter import messagebox

class Node:
    """A class representing a node in a linked list."""
    def __init__(self, data):
        self.data = data
        self.next = None


class LinkedList:
    """A linked list class for managing transactions."""
    def __init__(self):
        self.head = None

    def add(self, data):
        """Add a new node with the given data to the beginning of the list."""
        new_node = Node(data)
        new_node.next = self.head
        self.head = new_node

    def display(self):
        """Return a list of all transaction data in the linked list."""
        current = self.head
        transactions = []
        while current:
            transactions.append(current.data)
            current = current.next
        return transactions


class EstateManagement:
    """A class for managing properties and their transactions."""
    def __init__(self):
        self.properties = {}

    def add_property(self, property_id, metadata):
        """Add a new property with the given ID and metadata."""
        if property_id in self.properties:
            return f"Property ID {property_id} already exists."
        else:
            self.properties[property_id] = {
                "metadata": metadata,
                "transactions": LinkedList()
            }
            return f"Property {property_id} added successfully."

    def update_metadata(self, property_id, new_metadata):
        """Update metadata for a specific property."""
        if property_id in self.properties:
            self.properties[property_id]["metadata"].update(new_metadata)
            return f"Metadata for Property {property_id} updated successfully."
        else:
            return f"Property ID {property_id} not found."

    def add_transaction(self, property_id, transaction):
        """Add a transaction to a property's transaction list."""
        if property_id in self.properties:
            self.properties[property_id]["transactions"].add(transaction)
            return f"Transaction added to Property {property_id}."
        else:
            return f"Property ID {property_id} not found."

    def get_property(self, property_id):
        """Retrieve metadata and all transactions for a given property ID."""
        if property_id in self.properties:
            property_info = self.properties[property_id]
            return {
                "metadata": property_info["metadata"],
                "transactions": property_info["transactions"].display()
            }
        else:
            return None


def add_property_ui(manager):
    def submit():
        property_id = property_id_entry.get()
        owner = owner_entry.get()
        location = location_entry.get()
        try:
            value = int(value_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Property value must be a number.")
            return
        metadata = {"owner": owner, "location": location, "value": value}
        message = manager.add_property(property_id, metadata)
        messagebox.showinfo("Result", message)
        add_window.destroy()

    add_window = tk.Toplevel()
    add_window.title("Add Property")

    tk.Label(add_window, text="Property ID:").grid(row=0, column=0)
    property_id_entry = tk.Entry(add_window)
    property_id_entry.grid(row=0, column=1)

    tk.Label(add_window, text="Owner:").grid(row=1, column=0)
    owner_entry = tk.Entry(add_window)
    owner_entry.grid(row=1, column=1)

    tk.Label(add_window, text="Location:").grid(row=2, column=0)
    location_entry = tk.Entry(add_window)
    location_entry.grid(row=2, column=1)

    tk.Label(add_window, text="Value:").grid(row=3, column=0)
    value_entry = tk.Entry(add_window)
    value_entry.grid(row=3, column=1)

    tk.Button(add_window, text="Submit", command=submit).grid(row=4, column=0, columnspan=2)


def update_metadata_ui(manager):
    def submit():
        property_id = property_id_entry.get()
        key = key_entry.get()
        value = value_entry.get()
        try:
            value = int(value) if key == "value" else value
        except ValueError:
            messagebox.showerror("Error", "Invalid value type.")
            return
        message = manager.update_metadata(property_id, {key: value})
        messagebox.showinfo("Result", message)
        update_window.destroy()

    update_window = tk.Toplevel()
    update_window.title("Update Metadata")

    tk.Label(update_window, text="Property ID:").grid(row=0, column=0)
    property_id_entry = tk.Entry(update_window)
    property_id_entry.grid(row=0, column=1)

    tk.Label(update_window, text="Metadata Key:").grid(row=1, column=0)
    key_entry = tk.Entry(update_window)
    key_entry.grid(row=1, column=1)

    tk.Label(update_window, text="New Value:").grid(row=2, column=0)
    value_entry = tk.Entry(update_window)
    value_entry.grid(row=2, column=1)

    tk.Button(update_window, text="Submit", command=submit).grid(row=3, column=0, columnspan=2)


def add_transaction_ui(manager):
    def submit():
        property_id = property_id_entry.get()
        transaction = transaction_entry.get()
        message = manager.add_transaction(property_id, transaction)
        messagebox.showinfo("Result", message)
        transaction_window.destroy()

    transaction_window = tk.Toplevel()
    transaction_window.title("Add Transaction")

    tk.Label(transaction_window, text="Property ID:").grid(row=0, column=0)
    property_id_entry = tk.Entry(transaction_window)
    property_id_entry.grid(row=0, column=1)

    tk.Label(transaction_window, text="Transaction Details:").grid(row=1, column=0)
    transaction_entry = tk.Entry(transaction_window)
    transaction_entry.grid(row=1, column=1)

    tk.Button(transaction_window, text="Submit", command=submit).grid(row=2, column=0, columnspan=2)


def get_property_ui(manager):
    def submit():
        property_id = property_id_entry.get()
        details = manager.get_property(property_id)
        if details:
            metadata = details["metadata"]
            transactions = details["transactions"]
            result = f"Metadata: {metadata}\nTransactions: {', '.join(transactions)}"
        else:
            result = f"Property ID {property_id} not found."
        messagebox.showinfo("Property Details", result)
        details_window.destroy()

    details_window = tk.Toplevel()
    details_window.title("Get Property Details")

    tk.Label(details_window, text="Property ID:").grid(row=0, column=0)
    property_id_entry = tk.Entry(details_window)
    property_id_entry.grid(row=0, column=1)

    tk.Button(details_window, text="Submit", command=submit).grid(row=1, column=0, columnspan=2)


def main_ui():
    manager = EstateManagement()
    root = tk.Tk()
    root.title("Estate Management System")

    tk.Button(root, text="Add Property", command=lambda: add_property_ui(manager)).pack(pady=5)
    tk.Button(root, text="Update Metadata", command=lambda: update_metadata_ui(manager)).pack(pady=5)
    tk.Button(root, text="Add Transaction", command=lambda: add_transaction_ui(manager)).pack(pady=5)
    tk.Button(root, text="Get Property Details", command=lambda: get_property_ui(manager)).pack(pady=5)
    tk.Button(root, text="Exit", command=root.quit).pack(pady=5)

    root.mainloop()


if __name__ == "__main__":
    main_ui()



