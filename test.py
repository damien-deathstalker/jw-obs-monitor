import flet as ft

def main(page: ft.Page):
    # --- Window Configuration ---
    page.title = "JW OBS Monitor (Flet Edition)"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0  # Remove default padding to let the sidebar touch the edge
    page.window_width = 850
    page.window_height = 550

    # --- Actions ---
    def start_monitoring(e):
        status_text.value = "Status: Started Monitoring"
        page.update()

    def stop_monitoring(e):
        status_text.value = "Status: Stopped"
        page.update()

    def switch_scene(scene_name):
        status_text.value = f"Status: Switched OBS to '{scene_name}'"
        page.update()

    # ==========================================
    # LEFT SIDEBAR
    # ==========================================
    sidebar = ft.Container(
        width=220,
        bgcolor=ft.Colors.BLACK,  # Slightly lighter dark gray
        padding=20,
        content=ft.Column(
            controls=[
                ft.Text("Scenes", size=20, weight=ft.FontWeight.BOLD),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT), # Spacing
                
                # Scene Buttons
                ft.Button("Starting Soon", on_click=lambda _: switch_scene("Starting Soon"), width=200),
                ft.Button("Gameplay", on_click=lambda _: switch_scene("Gameplay"), width=200),
                ft.Button("Be Right Back", on_click=lambda _: switch_scene("Be Right Back"), width=200),
            ],
            spacing=15
        )
    )

    # ==========================================
    # RIGHT MAIN AREA
    # ==========================================
    status_text = ft.Text("Status: Idle", size=16, color=ft.Colors.GREY_400)

    # The "Preview" Box
    preview_box = ft.Container(
        content=ft.Text("Preview unavailable", color=ft.Colors.ON_SURFACE_VARIANT),
        alignment=ft.Alignment.CENTER,
        height=250,
        border=ft.Border.all(1, ft.Colors.OUTLINE),
        border_radius=10,
        bgcolor=ft.Colors.SURFACE,
    )

    main_content = ft.Container(
        expand=True, # Tells this container to fill all remaining horizontal space
        padding=30,
        content=ft.Column(
            controls=[
                ft.Text("Capture Preview", size=24, weight=ft.FontWeight.BOLD),
                preview_box,
                ft.Divider(height=40),
                
                # Status and Run Controls
                status_text,
                ft.Row(
                    controls=[
                        ft.FilledButton(
                            "Start", 
                            icon=ft.Icons.PLAY_ARROW, 
                            style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700),
                            on_click=start_monitoring
                        ),
                        ft.FilledButton(
                            "Stop", 
                            icon=ft.Icons.STOP, 
                            style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700),
                            on_click=stop_monitoring
                        ),
                    ],
                    spacing=20
                )
            ]
        )
    )

    # --- Construct the Layout ---
    # We place the sidebar and main content side-by-side in a Row
    layout = ft.Row(
        controls=[sidebar, main_content],
        expand=True,
        spacing=0 # No gap between sidebar and main content
    )

    page.add(layout)

if __name__ == "__main__":
    ft.run(main)