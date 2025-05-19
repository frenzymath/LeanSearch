def format_declaration(declaration):
    result : list[str] = []

    result.append("<declaration>")
    result.append(f"<docstring>{declaration['docstring']}</docstring>")
    result.append(f"<name>{declaration['name']}</name>")
    result.append(f"<signature>{declaration['description']}</signature>")
    result.append(f"<definition>{declaration['value']}</definition>")
    if declaration['informal_name'] is not None:
        result.append(f"<informal_name>{declaration['informal_name']}</informal_name>")
    if declaration['informal_description'] is not None:
        result.append(f"<informal_description>{declaration['informal_description']}</informal_description>")
    result.append("</declaration>")

    return "\n".join(result)

def format_input(input_data):
    result : list[str] = []

    result.append("<instructions>Your task is to create an informal description of the following metaprogramming declaration in Lean 4. Later on, we will use them to create embedding vectors.</instructions>")

    result.append(f"<file_docstring explanation='This is a docstring in the beginning of the .lean file where the declaration you are informalizing is located'>{input_data['header']}</file_docstring>")

    result.append("<neighbor_declarations explanation='These are the descriptions of the declarations that are located nearby in this Lean file.'>")
    for neighbor in input_data["neighbor"]:
        result.append(format_declaration(neighbor))
    result.append("</neighbor_declarations>")

    result.append("<dependent_declarations explanation='These are the descriptions of the declarations that our declaration depends on.'>")
    for dependency in input_data["dependency"]:
        result.append(format_declaration(dependency))
    result.append("</dependent_declarations>")

    result.append("<instructions>Finally, here is the declaration that you should create the description of.</instructions>")
    result.append(format_declaration(input_data))

    result.append("<instructions>Please put your informal description into the following format: <informal_name>...<informal_name> (this is where you put the informal name of this Lean 4 declaration), <informal_description>...</informal_description> (this is where you put the informal description of this Lean 4 declaration). You can put your thinking into <thinking>...</thinking> tags.</instructions>")

    return "\n".join(result)
