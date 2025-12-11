import sys
import os
import sqlite3
from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFontDatabase, QFont, QGuiApplication, QPalette, QColor, QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QDateEdit,
    QLabel,
    QCheckBox,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QFormLayout,
    QScrollArea,
    QGroupBox,
    QDialog,
    QInputDialog,
)


# --- Application metadata -------------------------------------------------

APP_NAME = "License Keeper"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Manage digital assets and their licenses"
APP_AUTHOR = "Arkaitz Redruello (redarkun)"
APP_LICENSE = "MIT"


# --- Paths & basic folders -----------------------------------------------

# APP_ROOT is the project root (two levels up from this file)
APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(APP_ROOT, "data")
EXPORTS_DIR = os.path.join(APP_ROOT, "exports")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "licenses.db")



class DatabaseManager:
    """Simple SQLite database manager for projects and assets."""

    def __init__(self, path: str = DB_PATH) -> None:
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if they do not exist yet and ensure new columns exist."""
        cur = self.conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT,
                usage TEXT,
                status TEXT,
                notes TEXT,
                use_legal_details INTEGER DEFAULT 0,
                use_project_usage INTEGER DEFAULT 0,
                use_tags INTEGER DEFAULT 0,
                use_asset_notes INTEGER DEFAULT 0
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                asset_type TEXT,
                author TEXT,
                source_url TEXT,
                download_date TEXT,
                license_type TEXT,
                custom_license TEXT,
                allow_commercial TEXT,
                allow_modifications TEXT,
                require_attribution TEXT,
                attribution_text TEXT,
                project_usage TEXT,
                internal_notes TEXT,
                tags TEXT,
                proof_path TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """
        )

        # En caso de que exista una base anterior sin proof_path, intentamos añadirla.
        try:
            cur.execute("ALTER TABLE assets ADD COLUMN proof_path TEXT")
        except sqlite3.OperationalError:
            # Columna ya existe, ignoramos.
            pass

        self.conn.commit()

    # --- Projects ----------------------------------------------------------

    def get_projects(self):
        """Return all projects ordered by name."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM projects ORDER BY name COLLATE NOCASE")
        return cur.fetchall()

    def add_project(self, data: dict) -> int:
        """Insert a new project and return its ID."""
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO projects (
                name, type, usage, status, notes,
                use_legal_details, use_project_usage, use_tags, use_asset_notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["name"],
                data.get("type"),
                data.get("usage"),
                data.get("status"),
                data.get("notes"),
                int(data.get("use_legal_details", False)),
                int(data.get("use_project_usage", False)),
                int(data.get("use_tags", False)),
                int(data.get("use_asset_notes", False)),
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_project(self, project_id: int, data: dict) -> None:
        """Update an existing project."""
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE projects SET
                name = ?, type = ?, usage = ?, status = ?, notes = ?,
                use_legal_details = ?, use_project_usage = ?,
                use_tags = ?, use_asset_notes = ?
            WHERE id = ?
            """,
            (
                data["name"],
                data.get("type"),
                data.get("usage"),
                data.get("status"),
                data.get("notes"),
                int(data.get("use_legal_details", False)),
                int(data.get("use_project_usage", False)),
                int(data.get("use_tags", False)),
                int(data.get("use_asset_notes", False)),
                project_id,
            ),
        )
        self.conn.commit()

    def delete_project(self, project_id: int) -> None:
        """Delete a project and its assets."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM assets WHERE project_id = ?", (project_id,))
        cur.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.conn.commit()

    def get_project(self, project_id: int):
        """Return a single project by ID."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        return cur.fetchone()

    # --- Assets ------------------------------------------------------------

    def get_assets_by_project(self, project_id: int):
        """Return assets for a project ordered by name."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM assets WHERE project_id = ? ORDER BY name COLLATE NOCASE",
            (project_id,),
        )
        return cur.fetchall()

    def add_asset(self, data: dict) -> int:
        """Insert an asset and return its ID."""
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO assets (
                project_id, name, asset_type, author, source_url,
                download_date, license_type, custom_license,
                allow_commercial, allow_modifications, require_attribution,
                attribution_text, project_usage, internal_notes, tags,
                proof_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["project_id"],
                data["name"],
                data.get("asset_type"),
                data.get("author"),
                data.get("source_url"),
                data.get("download_date"),
                data.get("license_type"),
                data.get("custom_license"),
                data.get("allow_commercial"),
                data.get("allow_modifications"),
                data.get("require_attribution"),
                data.get("attribution_text"),
                data.get("project_usage"),
                data.get("internal_notes"),
                data.get("tags"),
                data.get("proof_path"),
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_asset(self, asset_id: int, data: dict) -> None:
        """Update an existing asset."""
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE assets SET
                name = ?, asset_type = ?, author = ?, source_url = ?,
                download_date = ?, license_type = ?, custom_license = ?,
                allow_commercial = ?, allow_modifications = ?, require_attribution = ?,
                attribution_text = ?, project_usage = ?, internal_notes = ?, tags = ?,
                proof_path = ?
            WHERE id = ?
            """,
            (
                data["name"],
                data.get("asset_type"),
                data.get("author"),
                data.get("source_url"),
                data.get("download_date"),
                data.get("license_type"),
                data.get("custom_license"),
                data.get("allow_commercial"),
                data.get("allow_modifications"),
                data.get("require_attribution"),
                data.get("attribution_text"),
                data.get("project_usage"),
                data.get("internal_notes"),
                data.get("tags"),
                data.get("proof_path"),
                asset_id,
            ),
        )
        self.conn.commit()

    def delete_asset(self, asset_id: int) -> None:
        """Delete an asset."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
        self.conn.commit()
    def get_asset_type_usage(self) -> dict[str, int]:
        """Return a mapping {asset_type: count} for all types used in assets."""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT asset_type, COUNT(*) AS count
            FROM assets
            WHERE asset_type IS NOT NULL AND asset_type <> ''
            GROUP BY asset_type
            """
        )
        result: dict[str, int] = {}
        for row in cur.fetchall():
            result[row["asset_type"]] = row["count"]
        return result

    def rename_asset_type(self, old_type: str, new_type: str) -> None:
        """Rename an asset_type value globally in all assets."""
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE assets SET asset_type = ? WHERE asset_type = ?",
            (new_type, old_type),
        )
        self.conn.commit()


LICENSE_OPTIONS = [
    "Unknown",
    "CC0",
    "CC BY",
    "CC BY-SA",
    "CC BY-NC",
    "CC BY-NC-SA",
    "MIT",
    "GPL",
    "LGPL",
    "Proprietary",
    "Public domain (as stated)",
    "Other...",
]
# Built-in asset types (the ones that are always in the combo)
BUILTIN_ASSET_TYPES = [
    "Image / Sprite / Tileset",
    "Music",
    "SFX",
    "Font",
    "Code",
    "3D model",
]

# Special entry in the combo that means "custom type"
ASSET_TYPE_CUSTOM_SENTINEL = "Other… (custom)"

# Auto-completion data for legal fields based on license type
# Format: license_name -> (allow_commercial, allow_modifications, require_attribution)
LICENSE_AUTOCOMPLETION = {
    "CC0": ("Yes", "Yes", "No"),
    "CC BY": ("Yes", "Yes", "Yes"),
    "CC BY-SA": ("Yes", "Yes", "Yes"),
    "CC BY-NC": ("No", "Yes", "Yes"),
    "CC BY-NC-SA": ("No", "Yes", "Yes"),
    "MIT": ("Yes", "Yes", "Yes"),
    "GPL": ("Yes", "Yes", "Yes"),
    "LGPL": ("Yes", "Yes", "Yes"),
    "Public domain (as stated)": ("Yes", "Yes", "No"),
    "Proprietary": ("Not clear", "Not clear", "Not clear"),
}

class ProjectListItemWidget(QWidget):
    """Visual 'card' for a project in the list."""

    def __init__(self, name: str, meta: str = "", parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self.name_label = QLabel(name)
        name_font = self.name_label.font()
        name_font.setBold(True)
        self.name_label.setFont(name_font)

        layout.addWidget(self.name_label)

        if meta:
            self.meta_label = QLabel(meta)
            self.meta_label.setStyleSheet("color: rgb(200, 200, 200); font-style: italic;")
            layout.addWidget(self.meta_label)


class ProjectDialog(QDialog):
    """Simple form dialog to create or edit projects."""

    def __init__(self, db: DatabaseManager, project_id: int | None = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.setWindowTitle("Project")
        self._build_ui()

        if self.project_id is not None:
            self._load_project()

    def _build_ui(self) -> None:
        """Build the project form UI."""
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setSpacing(8)

        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["", "Game", "Application", "Tool", "Other"])

        self.usage_combo = QComboBox()
        self.usage_combo.addItems(["", "Personal", "Commercial", "Mixed / Undecided"])

        self.status_combo = QComboBox()
        self.status_combo.addItems(["", "In development", "Released", "Archived"])

        self.notes_edit = QTextEdit()

        # Asset field configuration for this project
        self.chk_legal_details = QCheckBox("Use legal details")
        self.chk_project_usage = QCheckBox("Use usage field")
        self.chk_asset_notes = QCheckBox("Use notes")

        form.addRow("Project name:", self.name_edit)
        form.addRow("Type:", self.type_combo)
        form.addRow("Intended use:", self.usage_combo)
        form.addRow("Status:", self.status_combo)
        form.addRow("Notes:", self.notes_edit)

        layout.addLayout(form)

        config_box = QGroupBox("Asset field configuration for this project")
        config_layout = QVBoxLayout(config_box)
        config_layout.setContentsMargins(8, 8, 8, 8)
        config_layout.setSpacing(4)
        config_layout.addWidget(self.chk_legal_details)
        config_layout.addWidget(self.chk_project_usage)
        config_layout.addWidget(self.chk_asset_notes)
        layout.addWidget(config_box)

        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save")
        self.btn_cancel = QPushButton("Cancel")
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.btn_save.clicked.connect(self._on_save)
        self.btn_cancel.clicked.connect(self.close)

    def _load_project(self) -> None:
        """Load data for an existing project into the form."""
        row = self.db.get_project(self.project_id)
        if row is None:
            return

        self.name_edit.setText(row["name"])
        self._set_combo_value(self.type_combo, row["type"])
        self._set_combo_value(self.usage_combo, row["usage"])
        self._set_combo_value(self.status_combo, row["status"])
        self.notes_edit.setPlainText(row["notes"] or "")

        self.chk_legal_details.setChecked(bool(row["use_legal_details"]))
        self.chk_project_usage.setChecked(bool(row["use_project_usage"]))
        self.chk_asset_notes.setChecked(bool(row["use_asset_notes"]))

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str | None) -> None:
        """Select a value in a combo if it exists."""
        if not value:
            combo.setCurrentIndex(0)
            return
        idx = combo.findText(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _collect_data(self) -> dict | None:
        """Validate and collect project form data."""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Project", "Project name is required.")
            return None

        data = {
            "name": name,
            "type": self.type_combo.currentText() or None,
            "usage": self.usage_combo.currentText() or None,
            "status": self.status_combo.currentText() or None,
            "notes": self.notes_edit.toPlainText().strip() or None,
            "use_legal_details": self.chk_legal_details.isChecked(),
            "use_project_usage": self.chk_project_usage.isChecked(),
            # Tags are not used in v1; keep column but always false.
            "use_tags": False,
            "use_asset_notes": self.chk_asset_notes.isChecked(),
        }
        return data

    def _on_save(self) -> None:
        """Save new or existing project."""
        data = self._collect_data()
        if data is None:
            return

        if self.project_id is None:
            self.project_id = self.db.add_project(data)
        else:
            self.db.update_project(self.project_id, data)

        # Notify parent to reload the project list
        parent = self.parent()
        if parent is not None and hasattr(parent, "_load_projects"):
            parent._load_projects()

        self.close()

class AssetTypeManagerDialog(QDialog):
    """Dialog to inspect and manage asset types (rename / delete with reassignment)."""

    def __init__(self, db: DatabaseManager, builtin_types: list[str], parent=None):
        super().__init__(parent)
        self.db = db
        self.builtin_types = set(builtin_types)
        self.types_changed = False

        self.setWindowTitle("Manage asset types")
        self.resize(500, 360)

        layout = QVBoxLayout(self)

        # Table: Type / Origin / Used by
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Type", "Origin", "Used by"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.btn_rename = QPushButton("Rename…")
        self.btn_delete = QPushButton("Delete…")
        btn_close = QPushButton("Close")

        btn_layout.addWidget(self.btn_rename)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

        self.btn_rename.clicked.connect(self._on_rename_clicked)
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        btn_close.clicked.connect(self.accept)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        self._reload_data()
        self._on_selection_changed()

    # --- Internal helpers --------------------------------------------------

    def _reload_data(self) -> None:
        """Reload the table from database stats."""
        usage = self.db.get_asset_type_usage()

        rows: list[tuple[str, str, int]] = []

        # Built-in types, even if their count is 0
        for name in sorted(self.builtin_types, key=str.lower):
            count = usage.pop(name, 0)
            rows.append((name, "Built-in", count))

        # Remaining types are custom
        for name, count in sorted(usage.items(), key=lambda kv: kv[0].lower()):
            if not name:
                continue
            rows.append((name, "Custom", count))

        self.table.setRowCount(len(rows))
        for row_idx, (name, origin, count) in enumerate(rows):
            self.table.setItem(row_idx, 0, QTableWidgetItem(name))
            self.table.setItem(row_idx, 1, QTableWidgetItem(origin))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(count)))

        if rows:
            self.table.selectRow(0)

    def _get_selected_info(self) -> tuple[str | None, str | None, int]:
        row = self.table.currentRow()
        if row < 0:
            return None, None, 0
        type_item = self.table.item(row, 0)
        origin_item = self.table.item(row, 1)
        used_item = self.table.item(row, 2)
        if not type_item or not origin_item or not used_item:
            return None, None, 0
        try:
            used = int(used_item.text())
        except ValueError:
            used = 0
        return type_item.text(), origin_item.text(), used

    def _on_selection_changed(self) -> None:
        """Enable/disable Rename/Delete depending on selection."""
        type_name, origin, used = self._get_selected_info()
        if type_name is None:
            self.btn_rename.setEnabled(False)
            self.btn_delete.setEnabled(False)
            return

        if origin == "Built-in":
            self.btn_rename.setEnabled(False)
            self.btn_delete.setEnabled(False)
        else:
            # Custom: rename always allowed, delete allowed (with reassignment if needed)
            self.btn_rename.setEnabled(True)
            self.btn_delete.setEnabled(True)

    # --- Actions -----------------------------------------------------------

    def _on_rename_clicked(self) -> None:
        type_name, origin, used = self._get_selected_info()
        if not type_name or origin != "Custom":
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Rename asset type",
            f"New name for '{type_name}':",
            text=type_name,
        )
        if not ok:
            return

        new_name = new_name.strip()
        if not new_name or new_name == type_name:
            return

        # Cannot collide with built-in
        if new_name in self.builtin_types:
            QMessageBox.warning(
                self,
                "Rename asset type",
                "You cannot rename a custom type to match a built-in type.",
            )
            return

        # Prevent collision with another existing type in the table
        for row in range(self.table.rowCount()):
            other = self.table.item(row, 0).text()
            if other == new_name:
                QMessageBox.warning(
                    self,
                    "Rename asset type",
                    "There is already an asset type with that name.",
                )
                return

        # Apply rename in DB
        self.db.rename_asset_type(type_name, new_name)
        self.types_changed = True
        self._reload_data()

    def _on_delete_clicked(self) -> None:
        type_name, origin, used = self._get_selected_info()
        if not type_name or origin != "Custom":
            return

        if used <= 0:
            # Not used by any asset: safe delete
            resp = QMessageBox.question(
                self,
                "Delete asset type",
                f"Delete custom asset type '{type_name}'?\n"
                f"It is not used by any asset.",
            )
            if resp != QMessageBox.Yes:
                return
            # Nothing to change in DB: this type only comes from usage stats.
            self.types_changed = True
            self._reload_data()
            return

        # Used by N assets: require reassignment
        usage = self.db.get_asset_type_usage()
        all_types = set(self.builtin_types) | set(usage.keys())
        if type_name in all_types:
            all_types.remove(type_name)

        candidates = sorted(t for t in all_types if t)
        if not candidates:
            QMessageBox.information(
                self,
                "Delete asset type",
                "There is no other asset type to reassign these assets to.",
            )
            return

        new_type, ok = QInputDialog.getItem(
            self,
            "Reassign assets",
            f"Type '{type_name}' is used by {used} assets.\n"
            "Choose a type to reassign them to:",
            candidates,
            0,
            False,
        )
        if not ok or not new_type:
            return

        # Reassign all assets of this type to the chosen type
        self.db.rename_asset_type(type_name, new_type)
        self.types_changed = True
        self._reload_data()

class MainWindow(QMainWindow):
    """Main window for the license and asset manager application."""

    def __init__(self) -> None:
        super().__init__()
        self.db = DatabaseManager()

        # --- Load Orbitron font --------------------------------------------
        font_path = os.path.join(
            APP_ROOT,
            "fonts",
            "Orbitron-Regular.ttf",
        )
        QFontDatabase.addApplicationFont(font_path)

        # Preconfigured Orbitron fonts for titles and main actions
        self.font_orbitron = QFont("Orbitron", 11)
        self.font_orbitron_bold = QFont("Orbitron", 12, QFont.Bold)

        self.current_project_id: int | None = None
        self.current_asset_id: int | None = None

        self.setWindowTitle("License Keeper")
        
        # Set window icon
        icon_path = os.path.join(APP_ROOT, "icons", "256icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.resize(1200, 700)
        self._build_ui()
        self._load_projects()

    def _build_ui(self) -> None:
        """Build the main window UI."""
        # --- Menu bar ------------------------------------------------------
        menubar = self.menuBar()
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About License Keeper", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
        # --- Main UI -------------------------------------------------------
        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)

        # --- Main content area ---------------------------------------------
        content_layout = QHBoxLayout()
        root_layout.addLayout(content_layout)


        # --- Project panel (left) ------------------------------------------
        left_panel = QVBoxLayout()
        left_panel.setSpacing(6)

        self.project_list = QListWidget()
        self.btn_new_project = QPushButton("New project")
        self.btn_edit_project = QPushButton("Edit project")
        self.btn_delete_project = QPushButton("Delete project")

        # Section title with Orbitron
        self.lbl_projects = QLabel("Projects")
        self.lbl_projects.setFont(self.font_orbitron_bold)
        left_panel.addWidget(self.lbl_projects)
        left_panel.addWidget(self.project_list)

        proj_btns = QHBoxLayout()
        proj_btns.addWidget(self.btn_new_project)
        proj_btns.addWidget(self.btn_edit_project)
        proj_btns.addWidget(self.btn_delete_project)

        left_panel.addLayout(proj_btns)

        content_layout.addLayout(left_panel, 1)

        # --- Central panel: asset list --------------------------------------
        center_panel = QVBoxLayout()
        center_panel.setSpacing(6)

        self.lbl_project_assets = QLabel("Project assets")
        self.lbl_project_assets.setFont(self.font_orbitron_bold)
        center_panel.addWidget(self.lbl_project_assets)

        # Asset type filter
        filter_row = QHBoxLayout()
        filter_label = QLabel("Filter by type:")
        self.asset_type_filter_combo = QComboBox()
        self.asset_type_filter_combo.addItem("All types")
        filter_row.addWidget(filter_label)
        filter_row.addWidget(self.asset_type_filter_combo, 1)
        filter_row.addStretch(2)
        center_panel.addLayout(filter_row)

        self.asset_table = QTableWidget(0, 4)
        self.asset_table.setHorizontalHeaderLabels(
            ["Name", "Type", "Author", "License"]
        )
        self.asset_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.asset_table.setSelectionMode(QTableWidget.SingleSelection)
        self.asset_table.horizontalHeader().setStretchLastSection(True)
        self.asset_table.setSortingEnabled(True)  # Enable column sorting

        center_panel.addWidget(self.asset_table)

        asset_btns = QHBoxLayout()
        self.btn_new_asset = QPushButton("New asset")
        self.btn_delete_asset = QPushButton("Delete asset")
        self.btn_export_txt = QPushButton("Export TXT/MD")

        asset_btns.addWidget(self.btn_new_asset)
        asset_btns.addWidget(self.btn_delete_asset)
        asset_btns.addWidget(self.btn_export_txt)
        center_panel.addLayout(asset_btns)

        content_layout.addLayout(center_panel, 2)

        # --- Right panel: asset form ---------------------------------------
        right_panel = QVBoxLayout()
        right_panel.setSpacing(6)

        self.asset_title_label = QLabel("Asset details")
        self.asset_title_label.setFont(self.font_orbitron_bold)
        right_panel.addWidget(self.asset_title_label)

        # Placeholder when there is no project
        self.asset_empty_label = QLabel("Select a project to view asset details.")
        self.asset_empty_label.setAlignment(Qt.AlignCenter)
        right_panel.addWidget(self.asset_empty_label)

        self.asset_scroll = QScrollArea()
        self.asset_scroll.setWidgetResizable(True)
        form_container = QWidget()
        self.asset_form_layout = QFormLayout(form_container)
        self.asset_form_layout.setSpacing(8)

        # Basic fields
        self.asset_name_edit = QLineEdit()

        # Asset type + custom
        # Asset type + custom + manage button
        self.asset_type_combo = QComboBox()
        self.asset_type_combo.addItems(
            [
                "",
                *BUILTIN_ASSET_TYPES,
                ASSET_TYPE_CUSTOM_SENTINEL,
            ]
        )
        # Solo un signal: trabajamos con el índice
        self.asset_type_combo.currentIndexChanged.connect(self._on_asset_type_changed)

        self.asset_custom_type_edit = QLineEdit()
        self.asset_custom_type_edit.setPlaceholderText("Custom asset type")
        self.asset_custom_type_edit.setEnabled(False)

        # Manage types button (gear)
        self.btn_manage_asset_types = QPushButton("⚙")
        self.btn_manage_asset_types.setFixedWidth(28)
        self.btn_manage_asset_types.setToolTip("Manage asset types…")

        type_row_widget = QWidget()
        type_row_layout = QHBoxLayout(type_row_widget)
        type_row_layout.setContentsMargins(0, 0, 0, 0)
        type_row_layout.setSpacing(4)
        type_row_layout.addWidget(self.asset_type_combo, 1)
        type_row_layout.addWidget(self.asset_custom_type_edit, 1)
        type_row_layout.addWidget(self.btn_manage_asset_types)


        self.asset_author_edit = QLineEdit()

        # URL + botones + aviso
        self.asset_url_edit = QLineEdit()
        self.asset_url_edit.setPlaceholderText("https://… (optional)")
        self.asset_open_url_btn = QPushButton("Open")
        self.asset_copy_url_btn = QPushButton("Copy")
        self.asset_url_warning_label = QLabel()
        self.asset_url_warning_label.setStyleSheet("color: #c04040;")
        self.asset_url_warning_label.setVisible(False)

        url_row_widget = QWidget()
        url_row_layout = QHBoxLayout(url_row_widget)
        url_row_layout.setContentsMargins(0, 0, 0, 0)
        url_row_layout.setSpacing(4)
        url_row_layout.addWidget(self.asset_url_edit, 1)
        url_row_layout.addWidget(self.asset_open_url_btn)
        url_row_layout.addWidget(self.asset_copy_url_btn)

        self.asset_date_edit = QDateEdit()
        self.asset_date_edit.setCalendarPopup(True)
        self.asset_date_edit.setDate(QDate.currentDate())

        self.license_combo = QComboBox()
        self.license_combo.addItems(LICENSE_OPTIONS)
        self.custom_license_edit = QLineEdit()
        self.custom_license_edit.setEnabled(False)

        # Proof file (archivo o carpeta)
        self.asset_proof_path_edit = QLineEdit()
        self.asset_proof_path_edit.setPlaceholderText(
            "Path to proof file/folder (zip, README, screenshot...)"
        )
        self.asset_browse_proof_btn = QPushButton("Browse…")
        self.asset_open_proof_btn = QPushButton("Open")

        proof_row_widget = QWidget()
        proof_row_layout = QHBoxLayout(proof_row_widget)
        proof_row_layout.setContentsMargins(0, 0, 0, 0)
        proof_row_layout.setSpacing(4)
        proof_row_layout.addWidget(self.asset_proof_path_edit, 1)
        proof_row_layout.addWidget(self.asset_browse_proof_btn)
        proof_row_layout.addWidget(self.asset_open_proof_btn)

        # Connection to enable/disable custom license field
        self.license_combo.currentTextChanged.connect(self._on_license_changed)

        self.asset_form_layout.addRow("Name / description:", self.asset_name_edit)
        self.asset_form_layout.addRow("Asset type:", type_row_widget)
        self.asset_form_layout.addRow("Source / author:", self.asset_author_edit)
        self.asset_form_layout.addRow("Source URL:", url_row_widget)
        self.asset_form_layout.addRow("", self.asset_url_warning_label)
        self.asset_form_layout.addRow("Download date:", self.asset_date_edit)
        self.asset_form_layout.addRow("License:", self.license_combo)
        self.asset_form_layout.addRow("Custom license:", self.custom_license_edit)
        self.asset_form_layout.addRow("Proof file/folder:", proof_row_widget)

        # Legal details group
        self.group_legal = QGroupBox("Legal details")
        legal_layout = QFormLayout(self.group_legal)
        legal_layout.setSpacing(6)
        self.cmb_allow_commercial = QComboBox()
        self.cmb_allow_commercial.addItems(["", "Yes", "No", "Not clear"])
        self.cmb_allow_modifications = QComboBox()
        self.cmb_allow_modifications.addItems(["", "Yes", "No", "Not clear"])
        self.cmb_require_attribution = QComboBox()
        self.cmb_require_attribution.addItems(["", "Yes", "No", "Not clear"])
        self.txt_attribution = QTextEdit()

        legal_layout.addRow("Allows commercial use:", self.cmb_allow_commercial)
        legal_layout.addRow("Allows modifications:", self.cmb_allow_modifications)
        legal_layout.addRow("Requires attribution:", self.cmb_require_attribution)
        legal_layout.addRow("Attribution text:", self.txt_attribution)

        # Usage group
        self.group_usage = QGroupBox("Usage")
        usage_layout = QFormLayout(self.group_usage)
        usage_layout.setSpacing(6)
        self.asset_where_used_edit = QLineEdit()
        usage_layout.addRow("Where used:", self.asset_where_used_edit)

        # Notes group
        self.group_notes = QGroupBox("Notes")
        notes_layout = QVBoxLayout(self.group_notes)
        notes_layout.setContentsMargins(8, 8, 8, 8)
        notes_layout.setSpacing(4)
        self.asset_notes_edit = QTextEdit()
        notes_layout.addWidget(self.asset_notes_edit)

        self.asset_form_layout.addRow(self.group_legal)
        self.asset_form_layout.addRow(self.group_usage)
        self.asset_form_layout.addRow(self.group_notes)

        # Save button
        self.btn_save_asset = QPushButton("Save asset changes")
        self.asset_form_layout.addRow(self.btn_save_asset)

        self.asset_scroll.setWidget(form_container)
        right_panel.addWidget(self.asset_scroll)

        content_layout.addLayout(right_panel, 2)

        self.setCentralWidget(central)

        # Connections
        self.project_list.currentRowChanged.connect(self._on_project_selected)
        self.btn_new_project.clicked.connect(self._on_new_project)
        self.btn_edit_project.clicked.connect(self._on_edit_project)
        self.btn_delete_project.clicked.connect(self._on_delete_project)

        self.btn_new_asset.clicked.connect(self._on_new_asset)
        self.btn_delete_asset.clicked.connect(self._on_delete_asset)
        self.asset_table.itemSelectionChanged.connect(self._on_asset_selected)
        self.btn_save_asset.clicked.connect(self._on_save_asset)
        self.btn_export_txt.clicked.connect(self._on_export_txt)
        self.asset_type_filter_combo.currentTextChanged.connect(self._on_asset_filter_changed)

        self.asset_open_url_btn.clicked.connect(self._on_open_asset_url)
        self.asset_copy_url_btn.clicked.connect(self._on_copy_asset_url)
        self.asset_browse_proof_btn.clicked.connect(self._on_browse_proof)
        self.asset_open_proof_btn.clicked.connect(self._on_open_proof)
        self.btn_manage_asset_types.clicked.connect(self._on_manage_asset_types)


        # Initially nothing selected
        self._set_asset_form_enabled(False)
        self._set_asset_panel_visible(False)
        self._update_buttons_enabled()

    # --- UI helpers --------------------------------------------------------

    def _set_asset_form_enabled(self, enabled: bool) -> None:
        """Enable or disable the asset form."""
        # Widgets que se activan/desactivan en bloque
        for widget in [
            self.asset_name_edit,
            self.asset_type_combo,
            self.asset_author_edit,
            self.asset_url_edit,
            self.asset_open_url_btn,
            self.asset_copy_url_btn,
            self.asset_date_edit,
            self.license_combo,
            self.asset_proof_path_edit,
            self.asset_browse_proof_btn,
            self.asset_open_proof_btn,
            self.group_legal,
            self.group_usage,
            self.group_notes,
            self.btn_save_asset,
        ]:
            widget.setEnabled(enabled)

        # Custom fields controlados por su propia lógica
        if enabled:
            # Reaplicamos las reglas de dependencia
            self._on_license_changed(self.license_combo.currentText())
            self._on_asset_type_changed(self.asset_type_combo.currentIndex())
        else:
            self.custom_license_edit.setEnabled(False)
            self.asset_custom_type_edit.setEnabled(False)


    def _set_asset_panel_visible(self, visible: bool) -> None:
        """Show the asset form or the empty placeholder."""
        self.asset_title_label.setVisible(visible)
        self.asset_scroll.setVisible(visible)
        self.asset_empty_label.setVisible(not visible)

    def _update_buttons_enabled(self) -> None:
        """Enable/disable buttons based on current state."""
        has_project = self.current_project_id is not None
        has_projects_any = bool(getattr(self, "projects_cache", []))
        has_assets_any = bool(getattr(self, "assets_cache", []))

        # Top bar
        self.btn_new_project.setEnabled(True)
        self.btn_new_asset.setEnabled(has_project)
        self.btn_export_txt.setEnabled(has_project)

        # Project panel
        self.btn_edit_project.setEnabled(has_project)
        self.btn_delete_project.setEnabled(has_project and has_projects_any)

        # Asset panel
        self.btn_delete_asset.setEnabled(has_assets_any)
    def _rebuild_asset_type_combo_from_db(self) -> None:
        """
        Rebuild the asset_type combo from built-in types + types found in DB.

        Keeps the current logical selection if possible.
        """
        # Determine what we want selected after rebuilding
        current_combo_text = self.asset_type_combo.currentText().strip()
        custom_text = self.asset_custom_type_edit.text().strip()
        if current_combo_text == ASSET_TYPE_CUSTOM_SENTINEL and custom_text:
            desired_value = custom_text
        else:
            desired_value = current_combo_text or None

        usage = self.db.get_asset_type_usage()

        self.asset_type_combo.blockSignals(True)
        self.asset_type_combo.clear()
        self.asset_type_combo.addItem("")  # empty

        for name in sorted(BUILTIN_ASSET_TYPES, key=str.lower):
            self.asset_type_combo.addItem(name)

        # Custom types discovered from DB (excluding built-ins and empty)
        custom_types = sorted(
            t for t in usage.keys() if t and t not in BUILTIN_ASSET_TYPES
        )
        for t in custom_types:
            if self.asset_type_combo.findText(t) == -1:
                self.asset_type_combo.addItem(t)

        self.asset_type_combo.addItem(ASSET_TYPE_CUSTOM_SENTINEL)
        self.asset_type_combo.blockSignals(False)

        # Reapply selection
        self._set_asset_type_from_value(desired_value)

    def _on_manage_asset_types(self) -> None:
        """Open the Manage asset types dialog."""
        dlg = AssetTypeManagerDialog(self.db, BUILTIN_ASSET_TYPES, parent=self)
        result = dlg.exec()
        if result == QDialog.Accepted and dlg.types_changed:
            # Rebuild combo from DB and refresh current project assets
            self._rebuild_asset_type_combo_from_db()
            self._load_assets_for_current_project()

    def _load_projects(self) -> None:
        """Fill the project list from the database."""
        self.project_list.clear()
        self.projects_cache: list[sqlite3.Row] = list(self.db.get_projects())

        for row in self.projects_cache:
            item = QListWidgetItem()
            meta_parts = []
            if row["type"]:
                meta_parts.append(row["type"])
            if row["status"]:
                meta_parts.append(row["status"])
            meta = " · ".join(meta_parts)
            widget = ProjectListItemWidget(row["name"], meta)
            item.setSizeHint(widget.sizeHint())
            self.project_list.addItem(item)
            self.project_list.setItemWidget(item, widget)

        if self.projects_cache:
            self.project_list.setCurrentRow(0)
        else:
            self.current_project_id = None
            self._clear_assets_table()
            self._clear_asset_form()
            self._set_asset_form_enabled(False)
            self._set_asset_panel_visible(False)

        self._update_buttons_enabled()

    def _current_project_row(self) -> sqlite3.Row | None:
        """Return the currently selected project row."""
        idx = self.project_list.currentRow()
        if idx < 0 or idx >= len(self.projects_cache):
            return None
        return self.projects_cache[idx]

    def _load_assets_for_current_project(self) -> None:
        """Load assets for the selected project."""
        row = self._current_project_row()
        if row is None:
            self.current_project_id = None
            self._clear_assets_table()
            self._clear_asset_form()
            self._set_asset_form_enabled(False)
            self._set_asset_panel_visible(False)
            self._update_buttons_enabled()
            return

        self.current_project_id = row["id"]

        assets = list(self.db.get_assets_by_project(self.current_project_id))
        self.assets_cache = assets
        
        # Update asset type filter combo with types from this project
        self._update_asset_type_filter(assets)
        
        # Disable sorting temporarily while populating to avoid issues
        self.asset_table.setSortingEnabled(False)
        self.asset_table.setRowCount(len(assets))

        for i, asset in enumerate(assets):
            self.asset_table.setItem(i, 0, QTableWidgetItem(asset["name"]))
            self.asset_table.setItem(i, 1, QTableWidgetItem(asset["asset_type"] or ""))
            self.asset_table.setItem(i, 2, QTableWidgetItem(asset["author"] or ""))
            self.asset_table.setItem(i, 3, QTableWidgetItem(asset["license_type"] or ""))

        # Re-enable sorting
        self.asset_table.setSortingEnabled(True)
        
        # Apply current filter
        self._apply_asset_filter()

        # Apply project field configuration to the form groups
        self._apply_project_field_config(row)

        if assets:
            self.asset_table.selectRow(0)
            self._set_asset_form_enabled(True)
        else:
            self.current_asset_id = None
            self._clear_asset_form()
            self._set_asset_form_enabled(True)

        self._set_asset_panel_visible(True)
        self._update_buttons_enabled()

    def _clear_assets_table(self) -> None:
        """Clear the asset table."""
        self.asset_table.setRowCount(0)
        self.assets_cache = []

    def _clear_asset_form(self) -> None:
        """Reset the asset form controls."""
        self.current_asset_id = None
        self.asset_name_edit.clear()
        self.asset_type_combo.setCurrentIndex(0)
        self.asset_custom_type_edit.clear()
        self.asset_custom_type_edit.setEnabled(False)
        self.asset_author_edit.clear()
        self.asset_url_edit.clear()
        self.asset_url_warning_label.setVisible(False)
        self.asset_url_edit.setStyleSheet("")
        self.asset_date_edit.setDate(QDate.currentDate())
        self.license_combo.setCurrentIndex(0)
        self.custom_license_edit.clear()
        self.custom_license_edit.setEnabled(False)
        self.cmb_allow_commercial.setCurrentIndex(0)
        self.cmb_allow_modifications.setCurrentIndex(0)
        self.cmb_require_attribution.setCurrentIndex(0)
        self.txt_attribution.clear()
        self.asset_where_used_edit.clear()
        self.asset_notes_edit.clear()
        self.asset_proof_path_edit.clear()

    def _apply_project_field_config(self, proj_row: sqlite3.Row) -> None:
        """Show/hide form groups according to project configuration."""
        use_legal = bool(proj_row["use_legal_details"])
        use_usage = bool(proj_row["use_project_usage"])
        use_notes = bool(proj_row["use_asset_notes"])

        self.group_legal.setVisible(use_legal)
        self.group_usage.setVisible(use_usage)
        self.group_notes.setVisible(use_notes)

    def _update_asset_type_filter(self, assets: list[sqlite3.Row]) -> None:
        """Update the asset type filter combo with types from current project."""
        # Get unique asset types from current assets
        asset_types = set()
        for asset in assets:
            asset_type = asset["asset_type"]
            if asset_type and asset_type.strip():
                asset_types.add(asset_type)
        
        # Block signals to avoid triggering filter while updating
        self.asset_type_filter_combo.blockSignals(True)
        current_filter = self.asset_type_filter_combo.currentText()
        
        self.asset_type_filter_combo.clear()
        self.asset_type_filter_combo.addItem("All types")
        
        for asset_type in sorted(asset_types):
            self.asset_type_filter_combo.addItem(asset_type)
        
        # Restore previous filter if it still exists
        idx = self.asset_type_filter_combo.findText(current_filter)
        if idx >= 0:
            self.asset_type_filter_combo.setCurrentIndex(idx)
        else:
            self.asset_type_filter_combo.setCurrentIndex(0)
        
        self.asset_type_filter_combo.blockSignals(False)

    def _apply_asset_filter(self) -> None:
        """Apply the current asset filter to the table."""
        filter_text = self.asset_type_filter_combo.currentText()
        
        for row in range(self.asset_table.rowCount()):
            if filter_text == "All types":
                self.asset_table.setRowHidden(row, False)
            else:
                type_item = self.asset_table.item(row, 1)  # Type column
                if type_item:
                    row_type = type_item.text()
                    self.asset_table.setRowHidden(row, row_type != filter_text)
                else:
                    self.asset_table.setRowHidden(row, True)

    def _on_asset_filter_changed(self, _text: str) -> None:
        """Called when the asset type filter changes."""
        self._apply_asset_filter()

    # --- Project slots -----------------------------------------------------

    def _on_new_project(self) -> None:
        """Create a new project."""
        dlg = ProjectDialog(self.db, project_id=None, parent=self)
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.show()

    def _on_edit_project(self) -> None:
        """Edit the currently selected project."""
        row = self._current_project_row()
        if row is None:
            QMessageBox.information(self, "Projects", "No project selected.")
            return

        dlg = ProjectDialog(self.db, project_id=row["id"], parent=self)
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.show()

    def _on_delete_project(self) -> None:
        """Delete the currently selected project after confirmation."""
        row = self._current_project_row()
        if row is None:
            return

        resp = QMessageBox.question(
            self,
            "Delete project",
            f"Are you sure you want to delete project '{row['name']}' and all its assets?",
        )
        if resp != QMessageBox.Yes:
            return

        self.db.delete_project(row["id"])
        self._load_projects()

    def _on_project_selected(self, _index: int) -> None:
        """Called when the selected project changes."""
        self._load_assets_for_current_project()

    # --- Asset slots -------------------------------------------------------

    def _on_new_asset(self) -> None:
        """Create a new empty asset in the form."""
        if self.current_project_id is None:
            QMessageBox.information(
                self, "Assets", "Create or select a project first."
            )
            return

        self._set_asset_form_enabled(True)
        self._set_asset_panel_visible(True)
        self._clear_asset_form()
        self.asset_name_edit.setFocus()
        self._update_buttons_enabled()

    def _current_asset_row(self) -> sqlite3.Row | None:
        """Return the currently selected asset row in the table."""
        idx = self.asset_table.currentRow()
        if idx < 0 or idx >= len(getattr(self, "assets_cache", [])):
            return None
        return self.assets_cache[idx]

    def _on_asset_selected(self) -> None:
        """Load selected asset data into the form."""
        row = self._current_asset_row()
        if row is None:
            self.current_asset_id = None
            self._update_buttons_enabled()
            return

        self.current_asset_id = row["id"]
        self._set_asset_form_enabled(True)
        self._set_asset_panel_visible(True)

        self.asset_name_edit.setText(row["name"])
        self._set_asset_type_from_value(row["asset_type"])
        self.asset_author_edit.setText(row["author"] or "")
        self.asset_url_edit.setText(row["source_url"] or "")
        self._validate_asset_url()

        try:
            if row["download_date"]:
                y, m, d = map(int, row["download_date"].split("-"))
                self.asset_date_edit.setDate(QDate(y, m, d))
            else:
                self.asset_date_edit.setDate(QDate.currentDate())
        except Exception:
            self.asset_date_edit.setDate(QDate.currentDate())

        self._set_combo_value(self.license_combo, row["license_type"])
        self.custom_license_edit.setText(row["custom_license"] or "")
        self.custom_license_edit.setEnabled(
            self.license_combo.currentText() == "Other..."
        )

        self._set_combo_value(self.cmb_allow_commercial, row["allow_commercial"])
        self._set_combo_value(self.cmb_allow_modifications, row["allow_modifications"])
        self._set_combo_value(self.cmb_require_attribution, row["require_attribution"])
        self.txt_attribution.setPlainText(row["attribution_text"] or "")

        self.asset_where_used_edit.setText(row["project_usage"] or "")
        self.asset_notes_edit.setPlainText(row["internal_notes"] or "")
        self.asset_proof_path_edit.setText(row["proof_path"] or "")

        self._update_buttons_enabled()

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str | None) -> None:
        """Select a value in a combo if it exists, otherwise clear selection."""
        if not value:
            combo.setCurrentIndex(0)
            return
        idx = combo.findText(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _collect_asset_data(self) -> dict | None:
        """Validate and collect asset form data."""
        if self.current_project_id is None:
            QMessageBox.warning(
                self, "Assets", "No project selected for this asset."
            )
            return None

        name = self.asset_name_edit.text().strip()
        if not name:
            QMessageBox.warning(
                self, "Assets", "Asset name/description is required."
            )
            return None

        # Simple ISO date
        qdate = self.asset_date_edit.date()
        download_date = f"{qdate.year():04d}-{qdate.month():02d}-{qdate.day():02d}"

        license_type = self.license_combo.currentText()
        custom_license = self.custom_license_edit.text().strip() or None
        if license_type == "Other..." and not custom_license:
            QMessageBox.warning(
                self,
                "License",
                "You selected 'Other...' but did not fill in the custom license.",
            )
            return None

        # --- Asset type (includes custom and combo update) ------------------
        asset_type_value = self._get_asset_type_value()
        # If ASSET_TYPE_CUSTOM_SENTINEL is selected but no custom text was provided,
        # _get_asset_type_value shows a warning and returns None → cancel save.
        if asset_type_value is None and (
            self.asset_type_combo.currentText().strip() == ASSET_TYPE_CUSTOM_SENTINEL
        ):
            return None



        data = {
            "project_id": self.current_project_id,
            "name": name,
            "asset_type": asset_type_value,
            "author": self.asset_author_edit.text().strip() or None,
            "source_url": self.asset_url_edit.text().strip() or None,
            "download_date": download_date,
            "license_type": license_type,
            "custom_license": custom_license,
            "allow_commercial": self.cmb_allow_commercial.currentText() or None,
            "allow_modifications": self.cmb_allow_modifications.currentText() or None,
            "require_attribution": self.cmb_require_attribution.currentText() or None,
            "attribution_text": self.txt_attribution.toPlainText().strip() or None,
            "project_usage": self.asset_where_used_edit.text().strip() or None,
            "internal_notes": self.asset_notes_edit.toPlainText().strip() or None,
            # Tags field kept for schema compatibility, but unused in v1.
            "tags": None,
            "proof_path": self.asset_proof_path_edit.text().strip() or None,
        }
        return data

    def _on_save_asset(self) -> None:
        """Save the current asset (new or existing)."""
        data = self._collect_asset_data()
        if data is None:
            return

        if self.current_asset_id is None:
            self.current_asset_id = self.db.add_asset(data)
        else:
            self.db.update_asset(self.current_asset_id, data)

        self._load_assets_for_current_project()

    def _on_delete_asset(self) -> None:
        """Delete the selected asset."""
        row = self._current_asset_row()
        if row is None:
            return

        resp = QMessageBox.question(
            self,
            "Delete asset",
            f"Are you sure you want to delete asset '{row['name']}'?",
        )
        if resp != QMessageBox.Yes:
            return

        self.db.delete_asset(row["id"])
        self._load_assets_for_current_project()

    def _on_license_changed(self, text: str) -> None:
        """Enable/disable custom license field based on license selection."""
        self.custom_license_edit.setEnabled(text == "Other...")
        # Auto-fill legal fields based on known licenses
        self._autofill_legal_fields(text)

    def _autofill_legal_fields(self, license_name: str) -> None:
        """Auto-complete legal fields based on the selected license."""
        if license_name in LICENSE_AUTOCOMPLETION:
            commercial, modifications, attribution = LICENSE_AUTOCOMPLETION[license_name]
            self._set_combo_value(self.cmb_allow_commercial, commercial)
            self._set_combo_value(self.cmb_allow_modifications, modifications)
            self._set_combo_value(self.cmb_require_attribution, attribution)

    # --- Asset type helpers -----------------------------------------------


    def _on_asset_type_changed(self, index: int) -> None:
        """Enable/disable custom asset type based on combo selection."""
        text = self.asset_type_combo.itemText(index)
        is_custom = (text == ASSET_TYPE_CUSTOM_SENTINEL)
        self.asset_custom_type_edit.setEnabled(is_custom)
        if not is_custom:
            self.asset_custom_type_edit.clear()

    def _get_asset_type_value(self) -> str | None:
        """
        Return the effective asset_type to store.

        - If ASSET_TYPE_CUSTOM_SENTINEL is selected, requires a custom text,
          adds it to the combo if not present, and returns that text.
        - Otherwise, returns the combo text or None.
        """
        combo_text = self.asset_type_combo.currentText().strip()

        if combo_text == ASSET_TYPE_CUSTOM_SENTINEL:
            custom = self.asset_custom_type_edit.text().strip()
            if not custom:
                QMessageBox.warning(
                    self,
                    "Assets",
                    "Please enter a custom asset type or choose one from the list.",
                )
                return None

            # Add new type to combo if not already there
            if self.asset_type_combo.findText(custom) == -1:
                sentinel_idx = self.asset_type_combo.findText(ASSET_TYPE_CUSTOM_SENTINEL)
                if sentinel_idx == -1:
                    self.asset_type_combo.addItem(custom)
                else:
                    self.asset_type_combo.insertItem(sentinel_idx, custom)

            return custom

        return combo_text or None

    def _set_asset_type_from_value(self, value: str | None) -> None:
        """
        Set combo + custom field based on stored value.

        If the value is not present in the combo, treat it as a custom type:
        select ASSET_TYPE_CUSTOM_SENTINEL and fill the custom field.
        """
        value = (value or "").strip()
        if not value:
            self.asset_type_combo.setCurrentIndex(0)
            self.asset_custom_type_edit.clear()
            self.asset_custom_type_edit.setEnabled(False)
            return

        idx = self.asset_type_combo.findText(value)
        if idx >= 0:
            # Value already in list → select it
            self.asset_type_combo.setCurrentIndex(idx)
            # _on_asset_type_changed handles custom field state
            return

        # Not in list: treat as custom
        sentinel_idx = self.asset_type_combo.findText(ASSET_TYPE_CUSTOM_SENTINEL)
        if sentinel_idx >= 0:
            self.asset_type_combo.setCurrentIndex(sentinel_idx)
            self.asset_custom_type_edit.setEnabled(True)
            self.asset_custom_type_edit.setText(value)
        else:
            # Fallback
            self.asset_type_combo.setCurrentIndex(0)
            self.asset_custom_type_edit.clear()
            self.asset_custom_type_edit.setEnabled(False)



    # --- URL helpers -------------------------------------------------------

    def _validate_asset_url(self) -> bool:
        """Validate URL minimally and show a warning if suspicious."""
        url = self.asset_url_edit.text().strip()
        if not url:
            self.asset_url_warning_label.setVisible(False)
            self.asset_url_edit.setStyleSheet("")
            return False

        if url.startswith("http://") or url.startswith("https://"):
            self.asset_url_warning_label.setVisible(False)
            self.asset_url_edit.setStyleSheet("")
            return True

        self.asset_url_warning_label.setText(
            "URL does not look valid (missing http:// or https://)."
        )
        self.asset_url_warning_label.setVisible(True)
        self.asset_url_edit.setStyleSheet(
            "border: 1px solid #c04040; border-radius: 3px;"
        )
        return False

    def _on_open_asset_url(self) -> None:
        """Open asset URL in browser if it seems minimally valid."""
        import webbrowser

        url = self.asset_url_edit.text().strip()
        if not url:
            return

        if not self._validate_asset_url():
            reply = QMessageBox.question(
                self,
                "Suspicious URL",
                "The URL does not look valid.\nOpen it anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        webbrowser.open(url)

    def _on_copy_asset_url(self) -> None:
        """Copy asset URL to clipboard."""
        url = self.asset_url_edit.text().strip()
        if not url:
            return
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(url)

    # --- Proof file helpers -----------------------------------------------

    def _on_browse_proof(self) -> None:
        """Choose file or folder for proof_path."""
        choice = QMessageBox.question(
            self,
            "Proof type",
            "Do you want to select a file?\n"
            "If you answer 'No', you will be able to select a folder.",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )

        if choice == QMessageBox.Cancel:
            return

        if choice == QMessageBox.Yes:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Select proof file",
                "",
                "All files (*.*)",
            )
        else:
            path = QFileDialog.getExistingDirectory(
                self,
                "Select proof folder",
                "",
            )

        if path:
            self.asset_proof_path_edit.setText(path)

    def _on_open_proof(self) -> None:
        """Open proof_path (file or folder) using the OS."""
        raw_path = self.asset_proof_path_edit.text().strip()
        if not raw_path:
            return

        path = Path(raw_path)
        if not path.exists():
            QMessageBox.warning(
                self,
                "Invalid path",
                "The proof file/folder path does not exist.",
            )
            return

        try:
            os.startfile(path)  # Windows
        except AttributeError:
            if os.name == "posix":
                import subprocess

                subprocess.Popen(["xdg-open", str(path)])
            else:
                QMessageBox.information(
                    self,
                    "Not supported",
                    "Could not open this path automatically on this system.",
                )

    # --- Export ------------------------------------------------------------

    def _on_export_txt(self) -> None:
        """Export current project's report to TXT or MD."""
        row = self._current_project_row()
        if row is None:
            QMessageBox.information(
                self, "Export", "Select a project first."
            )
            return

        # Ask for TXT or MD using custom buttons
        msg = QMessageBox(self)
        msg.setWindowTitle("Export")
        msg.setText("Choose export format:")

        btn_md = msg.addButton("Markdown (.md)", QMessageBox.AcceptRole)
        btn_txt = msg.addButton("Text (.txt)", QMessageBox.AcceptRole)
        btn_cancel = msg.addButton("Cancel", QMessageBox.RejectRole)

        msg.exec()

        if msg.clickedButton() == btn_cancel:
            return
        use_md = msg.clickedButton() == btn_md

        file_filter = "Markdown (*.md)" if use_md else "Plain text (*.txt)"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save project report",
            EXPORTS_DIR,
            file_filter,
        )

        if not path:
            return

        assets = list(self.db.get_assets_by_project(row["id"]))
        content = self._build_report_content(row, assets, use_md=use_md)

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as e:
            QMessageBox.critical(
                self,
                "Export",
                f"Could not save file:\n{e}",
            )
            return

        QMessageBox.information(
            self,
            "Export",
            f"Report saved to:\n{path}",
        )

    def _build_report_content(
        self,
        proj_row: sqlite3.Row,
        assets: list[sqlite3.Row],
        use_md: bool = False,
    ) -> str:
        """Build the report text content in TXT or MD."""
        lines: list[str] = []

        if use_md:
            lines.append(f"# Project: {proj_row['name']}")
            if proj_row["type"]:
                lines.append(f"- Type: {proj_row['type']}")
            if proj_row["usage"]:
                lines.append(f"- Intended use: {proj_row['usage']}")
            if proj_row["status"]:
                lines.append(f"- Status: {proj_row['status']}")
            if proj_row["notes"]:
                lines.append("")
                lines.append("## Project notes")
                lines.append(proj_row["notes"])
            lines.append("")
            lines.append("## Assets")
        else:
            lines.append(f"Project: {proj_row['name']}")
            if proj_row["type"]:
                lines.append(f"Type: {proj_row['type']}")
            if proj_row["usage"]:
                lines.append(f"Intended use: {proj_row['usage']}")
            if proj_row["status"]:
                lines.append(f"Status: {proj_row['status']}")
            if proj_row["notes"]:
                lines.append("")
                lines.append("Project notes:")
                lines.append(proj_row["notes"])
            lines.append("")
            lines.append("=== Assets ===")

        use_legal = bool(proj_row["use_legal_details"])
        use_usage = bool(proj_row["use_project_usage"])
        use_notes = bool(proj_row["use_asset_notes"])

        for idx, asset in enumerate(assets, start=1):
            if use_md:
                lines.append("")
                lines.append(f"### {idx}) {asset['name']}")
            else:
                lines.append("")
                lines.append(f"{idx}) {asset['name']}")

            if asset["asset_type"]:
                lines.append(f"   Type: {asset['asset_type']}")
            if asset["author"]:
                lines.append(f"   Source/Author: {asset['author']}")
            if asset["source_url"]:
                lines.append(f"   URL: {asset['source_url']}")
            if asset["license_type"]:
                lines.append(f"   License: {asset['license_type']}")
            if asset["custom_license"]:
                lines.append(f"   Custom license: {asset['custom_license']}")
            if asset["download_date"]:
                lines.append(f"   Download date: {asset['download_date']}")
            if asset["proof_path"]:
                lines.append(f"   Proof file/folder: {asset['proof_path']}")

            if use_legal:
                lines.append("   [Legal details]")
                if asset["allow_commercial"]:
                    lines.append(
                        f"      Allows commercial use: {asset['allow_commercial']}"
                    )
                if asset["allow_modifications"]:
                    lines.append(
                        f"      Allows modifications: {asset['allow_modifications']}"
                    )
                if asset["require_attribution"]:
                    lines.append(
                        f"      Requires attribution: {asset['require_attribution']}"
                    )
                if asset["attribution_text"]:
                    lines.append("      Attribution text:")
                    for line in asset["attribution_text"].splitlines():
                        lines.append(f"         {line}")

            if use_usage and asset["project_usage"]:
                lines.append("   [Usage in project]")
                lines.append(f"      Where used: {asset['project_usage']}")

            if use_notes and asset["internal_notes"]:
                lines.append("   [Notes]")
                for line in asset["internal_notes"].splitlines():
                    lines.append(f"      {line}")

        return "\n".join(lines)

    def _show_about(self) -> None:
        """Show About dialog with application information."""
        about_text = f"""<html><body>
        <h2>{APP_NAME}</h2>
        <p><b>Version {APP_VERSION}</b></p>
        <p>{APP_DESCRIPTION}</p>
        <p><br></p>
        <p>Keep track of where you got your assets, what licenses they have,<br>
        and where you're using them in your projects.</p>
        <p><br></p>
        <p>Created by {APP_AUTHOR}</p>
        <p>License: {APP_LICENSE}</p>
        </body></html>"""
        
        QMessageBox.about(self, f"About {APP_NAME}", about_text)


def main() -> None:
    """Application entry point."""
    import traceback

    try:
        app = QApplication(sys.argv)

        # --- Dark mode global palette -------------------------------------
        app.setStyle("Fusion")
        dark_palette = QPalette()

        # Aplicar los mismos colores a todos los grupos (active/inactive/disabled)
        for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
            dark_palette.setColor(group, QPalette.Window, QColor(40, 40, 40))
            dark_palette.setColor(group, QPalette.WindowText, QColor(220, 220, 220))
            dark_palette.setColor(group, QPalette.Base, QColor(30, 30, 30))
            dark_palette.setColor(group, QPalette.AlternateBase, QColor(45, 45, 45))
            dark_palette.setColor(group, QPalette.ToolTipBase, QColor(40, 40, 40))
            dark_palette.setColor(group, QPalette.ToolTipText, QColor(220, 220, 220))
            dark_palette.setColor(group, QPalette.Text, QColor(220, 220, 220))
            dark_palette.setColor(group, QPalette.Button, QColor(50, 50, 50))
            dark_palette.setColor(group, QPalette.ButtonText, QColor(220, 220, 220))
            dark_palette.setColor(group, QPalette.BrightText, QColor(255, 0, 0))
            dark_palette.setColor(group, QPalette.Link, QColor(100, 149, 237))
            dark_palette.setColor(group, QPalette.Highlight, QColor(90, 110, 180))
            dark_palette.setColor(group, QPalette.HighlightedText, QColor(240, 240, 240))

        # Placeholder legible
        dark_palette.setColor(QPalette.PlaceholderText, QColor(160, 160, 160))

        app.setPalette(dark_palette)




        win = MainWindow()
        win.show()
        sys.exit(app.exec())

    except Exception:
        traceback.print_exc()
        input("\nERROR – Pulsa ENTER para cerrar...")


if __name__ == "__main__":
    main()


