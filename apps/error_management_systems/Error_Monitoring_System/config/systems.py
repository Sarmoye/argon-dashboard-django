SYSTEMS_CONFIG = {
    'CIS': {
        'directory': "/srv/itsea_files/cis_error_report_files",
        'headers': ['Domain', 'Service Type', 'Service Name', 'Error Count', 'Error Reason'],
        'skip_rows': 0,
        'recipients': ['Sarmoye.AmitoureHaidara@mtn.com'],
        'color': '#e74c3c',
        'icon': '🔴'
    },
    'ECW': {
        'directory': "/srv/itsea_files/ecw_error_report_files",
        'headers': ['Domain', 'Service Type', 'Service Name', 'Error Count'],
        'skip_rows': 0,
        'recipients': ['Sarmoye.AmitoureHaidara@mtn.com'],
        'color': '#27ae60',
        'icon': '🟢'
    },
    'IRM': {
        'directory': "/srv/itsea_files/irm_error_report_files",
        'headers': ['Domain', 'Service Type', 'Service Name', 'Error Count', 'Error Reason'],
        'skip_rows': 1,
        'recipients': ['Sarmoye.AmitoureHaidara@mtn.com'],
        'color': '#f39c12',
        'icon': '🟡'
    }
}

# Pour ajouter un nouveau système, il suffit d'ajouter une entrée:
"""
'NEW_SYSTEM': {
    'directory': "/path/to/new/system/files",
    'headers': ['Domain', 'Service Type', 'Service Name', 'Error Count'],
    'skip_rows': 0,
    'recipients': ['email@example.com'],
    'color': '#3498db',
    'icon': '🔵'
}
"""