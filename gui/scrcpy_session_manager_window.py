import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import os
import shlex

from utils import scrcpy_handler

class ScrcpySessionManagerWindow:
    def __init__(self, parent_root, parent_x, parent_y, parent_width, close_callback):
        self.parent_root = parent_root
        self.close_callback = close_callback # Store the callback
        self.window = tk.Toplevel(parent_root)
        self.window.title("Active Scrcpy Sessions")

        self.window.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Load default placeholder icon
        try:
            self.default_icon_img = Image.open("gui/placeholder.png").resize((32, 32), Image.LANCZOS)
            self.default_icon = ImageTk.PhotoImage(self.default_icon_img)
        except (FileNotFoundError, NameError):
            self.default_icon_img = Image.new('RGBA', (32, 32), (60, 60, 60, 255))
            self.default_icon = ImageTk.PhotoImage(self.default_icon_img)

        # Load Winlator placeholder icon
        try:
            self.winlator_icon_img = Image.open("gui/winlator_placeholder.png").resize((32, 32), Image.LANCZOS)
            self.winlator_icon = ImageTk.PhotoImage(self.winlator_icon_img)
        except (FileNotFoundError, NameError):
            self.winlator_icon_img = Image.new('RGBA', (32, 32), (60, 60, 60, 255))
            self.winlator_icon = ImageTk.PhotoImage(self.winlator_icon_img)

        # Bind to the parent window's <Configure> event to track its position
        self._parent_configure_funcid = self.parent_root.bind('<Configure>', self._on_parent_configure)

        pos_x = parent_x + parent_width
        pos_y = parent_y
        self.window.geometry(f"300x400+{pos_x}+{pos_y}")

        # Configure Treeview style for font and size
        style = ttk.Style()
        style.configure("Treeview", font=("Helvetica", 12), rowheight=32)
        style.configure("Treeview.Heading", font=("Helvetica", 12, "bold")) # Optional: for column headers

        # Top button frame for Refresh
        self.button_frame = ttk.Frame(self.window)
        self.button_frame.pack(fill='x', pady=5)

        # Treeview for sessions
        self.tree = ttk.Treeview(self.window, show="tree") # Only show the tree column (default #0)
        self.tree.pack(fill='both', expand=True, padx=10, pady=5)

        # Schedule re-application of rowheight after a short delay
        self.window.after(250, lambda: style.configure("Treeview", rowheight=32))

        # Scrollbar for Treeview
        self.tree_scrollbar = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scrollbar.set)
        self.tree_scrollbar.pack(side='right', fill='y')

        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)

        # Bottom command buttons
        self.command_frame = ttk.Frame(self.window)
        self.command_frame.pack(fill='x', padx=10, pady=5)

        self.terminate_button = ttk.Button(self.command_frame, text="Terminate", command=self._terminate_selected_session, style="Small.TButton", state='disabled')
        self.terminate_button.pack(side='left', padx=5)

        self.command_button = ttk.Button(self.command_frame, text="Command Used", command=self._show_command_for_selected_session, style="Small.TButton", state='disabled')
        self.command_button.pack(side='left', padx=5)

        self.image_refs = [] # To prevent garbage collection of PhotoImage objects
        self.session_data_map = {}

        # Schedule initial population after the window is fully rendered
        self.window.after(0, self.populate_sessions)
        # Schedule the first auto-refresh after 5 seconds
        self.refresh_job = self.window.after(5000, self.auto_refresh_sessions)

    def _on_tree_select(self, event):
        selected_items = self.tree.selection()
        if selected_items:
            self.terminate_button.config(state='normal')
            self.command_button.config(state='normal')
        else:
            self.terminate_button.config(state='disabled')
            self.command_button.config(state='disabled')

    def populate_sessions(self):
        # Get currently selected item before clearing
        current_selection = self.tree.focus()

        for item in self.tree.get_children():
            self.tree.delete(item)
        self.image_refs.clear() # Clear old image references
        self.session_data_map.clear() # Clear old session data

        sessions = scrcpy_handler.get_active_scrcpy_sessions()

        if not sessions:
            self.tree.insert('', 'end', text="No active Scrcpy sessions.")
            # Clear selection if no sessions
            self.tree.selection_set(())
            self.tree.focus(())
            self._on_tree_select(None) # Update button states
            return

        reselect_item_id = None
        for session in sessions:
            icon_photo = None
            if session['icon_path'] and os.path.exists(session['icon_path']):
                try:
                    img = Image.open(session['icon_path']).resize((32, 32), Image.LANCZOS) # Smaller icon for Treeview
                    icon_photo = ImageTk.PhotoImage(img)
                    self.image_refs.append(icon_photo) # Keep a reference
                except Exception as e:
                    print(f"Error loading icon {session['icon_path']}: {e}")
            
            # Use default icon if no specific icon is loaded
            if icon_photo is None:
                if session.get('session_type') == 'winlator':
                    icon_photo = self.winlator_icon
                else:
                    icon_photo = self.default_icon

            self.tree.insert('', 'end',
                             text=session['app_name'],
                             image=icon_photo,
                             iid=str(session['pid']), # Use PID as item ID for easy lookup, convert to string
                             open=True # Ensure item is visible
                            )
            self.session_data_map[session['pid']] = session
            if str(session['pid']) == current_selection:
                reselect_item_id = current_selection

        if reselect_item_id and self.tree.exists(reselect_item_id):
            self.tree.selection_set(reselect_item_id)
            self.tree.focus(reselect_item_id)
        else:
            # If previous selection doesn't exist or no selection, select the first item
            first_item_id = self.tree.get_children()[0]
            self.tree.selection_set(first_item_id)
            self.tree.focus(first_item_id)

        self._on_tree_select(None) # Update button states after populating

    def _terminate_selected_session(self):
        selected_item_id = self.tree.focus()
        if not selected_item_id: return

        # Convert selected_item_id to int as session_data_map keys are integers
        session_data = self.session_data_map.get(int(selected_item_id))
        if not session_data: return
        pid = session_data['pid']
        app_name = session_data['app_name']

        if messagebox.askyesno("Confirm Termination", f"Are you sure you want to terminate {app_name} (PID: {pid})?"):
            if scrcpy_handler.kill_scrcpy_session(pid):
                print(f"Process killed")
            else:
                messagebox.showerror("Error", f"Could not terminate Scrcpy session for {app_name} (PID: {pid}).")
            self.populate_sessions() # Refresh the list after terminating

    def _show_command_for_selected_session(self):
        selected_item_id = self.tree.focus()
        if not selected_item_id: return

        # Convert selected_item_id to int as session_data_map keys are integers
        session_data = self.session_data_map.get(int(selected_item_id))
        if not session_data: return
        command_args = session_data.get('command_args', ["N/A"])
        command_str = shlex.join(command_args)

        # Create a new Toplevel window for displaying the command
        command_window = tk.Toplevel(self.window)
        command_window.title(f"Command for {session_data['app_name']}")
        command_window.geometry("600x200")
        command_window.transient(self.window)
        command_window.grab_set()

        text_frame = ttk.Frame(command_window)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)

        command_text = tk.Text(text_frame, wrap='word', height=10, width=70)
        command_text.config(state='normal') # Make it editable temporarily
        command_text.insert(tk.END, command_str)
        command_text.config(state='disabled') # Make it read-only again

        text_scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=command_text.yview)
        command_text.config(yscrollcommand=text_scrollbar.set)

        text_scrollbar.pack(side='right', fill='y')
        command_text.pack(side='left', fill='both', expand=True)

        # Add a close button
        close_button = ttk.Button(command_window, text="Close", command=command_window.destroy, style="Small.TButton")
        close_button.pack(pady=5)

        command_window.wait_window()

    def auto_refresh_sessions(self):
        self.populate_sessions()
        self.refresh_job = self.window.after(5000, self.auto_refresh_sessions) # Refresh every 5 seconds

    def _on_closing(self):
        if hasattr(self, 'refresh_job'):
            self.window.after_cancel(self.refresh_job)
        # Unbind the parent window's <Configure> event using the stored funcid
        self.parent_root.unbind('<Configure>', self._parent_configure_funcid)
        self.window.destroy()
        if self.close_callback:
            self.close_callback()

    def _on_parent_configure(self, event):
        # Check if the window still exists before trying to update its geometry
        if not self.window.winfo_exists():
            return
        # Recalculate position relative to the parent window's current absolute position
        new_x = self.parent_root.winfo_x() + self.parent_root.winfo_width()
        new_y = self.parent_root.winfo_y()
        self.window.geometry(f"300x400+{new_x}+{new_y}")

    # This method was not used by the buttons, but had an undefined 'app_name'
    # It's removed as it's not part of the button's functionality.
    # def kill_session(self, pid):
    #     if messagebox.askyesno("Confirm Termination", f"Are you sure you want to terminate {app_name} (PID: {pid})?"):
    #         if scrcpy_handler.kill_scrcpy_session(pid):
    #             messagebox.showinfo("Success", f"Scrcpy session for {app_name} (PID: {pid}) terminated.")
    #         else:
    #             messagebox.showerror("Error", f"Could not terminate Scrcpy session for {app_name} (PID: {pid}).")
    #         self.populate_sessions() # Refresh the list after terminating
