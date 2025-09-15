"""
Language configuration for tree-sitter parsing
"""

# Query patterns for different languages to extract key constructs
LANGUAGE_QUERIES = {
  'python': {
    'imports': '''
      (import_statement) @import
      (import_from_statement) @import
    ''',
    'definitions': '''
      (class_definition name: (identifier) @class.name) @class
      (function_definition name: (identifier) @function.name) @function
      (decorated_definition) @decorated
    ''',
    'structure': '''
      (module . (expression_statement (string))? @docstring)
      (class_definition
        name: (identifier) @class.name
        body: (block)? @class.body) @class
      (function_definition
        name: (identifier) @function.name
        parameters: (parameters)? @function.params) @function
    '''
  },
  'javascript': {
    'imports': '''
      (import_statement) @import
      (call_expression
        function: (identifier) @_require (#eq? @_require "require")) @require
    ''',
    'definitions': '''
      (class_declaration name: (identifier) @class.name) @class
      (function_declaration name: (identifier) @function.name) @function
      (method_definition name: (property_identifier) @method.name) @method
      (variable_declarator
        name: (identifier) @var.name
        value: (arrow_function)? @arrow) @variable
    ''',
    'structure': '''
      (program) @root
      (export_statement) @export
      (class_declaration) @class
      (function_declaration) @function
    '''
  },
  'typescript': {
    'imports': '''
      (import_statement) @import
    ''',
    'definitions': '''
      (class_declaration name: (type_identifier) @class.name) @class
      (interface_declaration name: (type_identifier) @interface.name) @interface
      (function_declaration name: (identifier) @function.name) @function
      (method_signature name: (property_identifier) @method.name) @method
      (type_alias_declaration name: (type_identifier) @type.name) @type
    ''',
    'structure': '''
      (interface_declaration) @interface
      (type_alias_declaration) @type_alias
      (enum_declaration) @enum
    '''
  },
  'java': {
    'imports': '''
      (import_declaration) @import
    ''',
    'definitions': '''
      (class_declaration name: (identifier) @class.name) @class
      (interface_declaration name: (identifier) @interface.name) @interface
      (method_declaration name: (identifier) @method.name) @method
      (constructor_declaration name: (identifier) @constructor.name) @constructor
    ''',
    'structure': '''
      (package_declaration) @package
      (class_declaration
        name: (identifier) @class.name
        body: (class_body)? @class.body) @class
    '''
  },
  'go': {
    'imports': '''
      (import_declaration) @import
    ''',
    'definitions': '''
      (type_declaration (type_spec name: (type_identifier) @type.name)) @type
      (function_declaration name: (identifier) @function.name) @function
      (method_declaration name: (field_identifier) @method.name) @method
    ''',
    'structure': '''
      (package_clause) @package
      (type_declaration) @type
      (function_declaration) @function
    '''
  },
  'rust': {
    'imports': '''
      (use_declaration) @import
    ''',
    'definitions': '''
      (struct_item name: (type_identifier) @struct.name) @struct
      (enum_item name: (type_identifier) @enum.name) @enum
      (function_item name: (identifier) @function.name) @function
      (impl_item type: (type_identifier) @impl.type) @impl
      (trait_item name: (type_identifier) @trait.name) @trait
    ''',
    'structure': '''
      (mod_item) @module
      (struct_item) @struct
      (impl_item) @implementation
    '''
  },
  'cpp': {
    'imports': '''
      (preproc_include) @include
    ''',
    'definitions': '''
      (class_specifier name: (type_identifier) @class.name) @class
      (function_definition declarator: (function_declarator declarator: (identifier) @function.name)) @function
      (struct_specifier name: (type_identifier) @struct.name) @struct
    ''',
    'structure': '''
      (namespace_definition) @namespace
      (class_specifier) @class
      (struct_specifier) @struct
    '''
  }
}

# Map file extensions to tree-sitter language names
EXTENSION_TO_LANGUAGE = {
  '.py': 'python',
  '.js': 'javascript',
  '.jsx': 'javascript',
  '.cjs': 'javascript',
  '.mjs': 'javascript',
  '.ts': 'typescript',
  '.tsx': 'typescript',
  '.mts': 'typescript',
  '.java': 'java',
  '.go': 'go',
  '.rs': 'rust',
  '.c': 'c',
  '.cpp': 'cpp',
  '.cc': 'cpp',
  '.cxx': 'cpp',
  '.h': 'c',
  '.hpp': 'cpp',
  '.cs': 'c_sharp',
  '.rb': 'ruby',
  '.php': 'php',
  '.swift': 'swift',
  '.kt': 'kotlin',
  '.scala': 'scala',
  '.r': 'r',
  '.m': 'objc',
  '.mm': 'objc',
}

# Entity type mappings for different languages
ENTITY_TYPES = {
  'python': {
    'class_definition': 'class',
    'function_definition': 'function',
  },
  'javascript': {
    'class_declaration': 'class',
    'function_declaration': 'function',
    'arrow_function': 'function',
    'method_definition': 'method',
  },
  'typescript': {
    'class_declaration': 'class',
    'interface_declaration': 'interface',
    'function_declaration': 'function',
    'method_signature': 'method',
    'type_alias_declaration': 'type',
  },
  'java': {
    'class_declaration': 'class',
    'interface_declaration': 'interface',
    'method_declaration': 'method',
    'constructor_declaration': 'constructor',
  },
  'go': {
    'type_declaration': 'type',
    'function_declaration': 'function',
    'method_declaration': 'method',
  },
  'rust': {
    'struct_item': 'struct',
    'enum_item': 'enum',
    'function_item': 'function',
    'impl_item': 'impl',
    'trait_item': 'trait',
  }
}
