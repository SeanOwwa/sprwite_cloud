from nicegui import ui


@ui.page("/editor_page")
def editor_page():
    
    ui.add_css("""
        body {
            margin: 0;
            background: #ffffff;
        }

        .full-editor {
            width: 100%;
            height: 100dvh;
        }

        .full-editor .q-editor {
            height: 100%;
            display: flex;
            flex-direction: column;
            background: #ffffff;
            border: none !important;
            box-shadow: none !important;
        }

        .full-editor .q-editor__toolbar,
        .full-editor .q-editor__content,
        .full-editor .q-editor__editable {
            background: #ffffff;
            border: none !important;
            box-shadow: none !important;
        }

        .full-editor .q-editor__content {
            font-family: Georgia, "Times New Roman", serif;
            font-size: 16pt !important;
        }

        .full-editor .q-editor__toolbar {
            display: none;
        }

        .full-editor .q-editor__content {
            flex: 1;
            min-height: 0;
            overflow-y: auto;
            box-sizing: border-box;
            width: 100%;
            max-width: 8.5in;
            margin-inline: auto;
            padding: 1in;
        }
    """)

    editor: ui.editor = ui.editor(
        placeholder='Type something here'
    ).classes('full-editor w-full flex-1').style(
        'height: 100%; min-height: 800px; background: #ffffff; border: none;'
    )

    menu_button: ui.button = ui.button(
        icon='menu',
        on_click=lambda: drawer.toggle()
    ).props('flat round dense').classes(
        'fixed top-3 left-3 z-50 text-black opacity-20'
    )

    with ui.left_drawer(value=True).classes(
        'bg-white p-2'
    ).style('width: 240px') as drawer:

        # Sidebar title and toggle
        with ui.row().classes(
            'w-full items-center justify-between p-2'
        ):
            ui.label('SPWRITE APP').classes(
                'text-sm font-bold'
            )

            ui.button(
                icon='menu',
                on_click=lambda: drawer.toggle()
            ).props('flat round dense').classes('text-black')

        ui.separator()

        with ui.column().classes('w-full gap-1 mt-3'):
            
            ui.button(
                'Project',
                icon='folder',
                on_click=lambda: ui.notify('Projects selected')
            ).props('flat align=left').classes(
                'w-full text-black'
            )

            ui.button(
                'Chapter 1',
                icon='description',
                on_click=lambda: ui.notify('Projects selected')
            ).props('flat align=left').classes(
                'w-full text-black'
            )

            ui.separator().classes('my-5')

            ui.button(
                'BACK DASHBOARD ',
                icon='arrow_back_ios',
                on_click=lambda: ui.navigate.back()
            ).props('flat align=left').classes(
                'w-full text-black mt-3'
            )