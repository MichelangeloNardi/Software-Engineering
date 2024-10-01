import re
import sys
import copy
import time


######################### Token validation #######################


class TokenizationError(Exception):
    pass

def tokenize(program):
    tokens = []
    token_spec = [
        ('KEYWORD', r'\b(var|show|show_ones|not|and|or|True|False)\b'),  # Keywords
        ('COMMENT', r'#.*'),            # Comment
        ('NUMBER', r'\d+'),             # Integer (should trigger an error if at the start of identifier)
        ('ID', r'[A-Za-z_][A-Za-z0-9_]*'),  # Identifier
        ('OP', r'[()=;]'),              # Special characters
        ('WHITESPACE', r'[ \t\r\n]+'),  # Whitespace
        ('INVALID', r'.'),              # Catch-all for invalid characters
    ]
    
    token_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_spec)
    for match in re.finditer(token_regex, program):
        kind = match.lastgroup
        value = match.group(kind)

        if kind == 'WHITESPACE' or kind == 'COMMENT':
            continue  # Ignore whitespace and comments

        if kind == 'INVALID':
            raise TokenizationError(f"Invalid character in input: '{value}'")

        if kind == 'NUMBER':
            raise TokenizationError(f"Invalid identifier starting with number: '{value}'")

        tokens.append((kind, value))

    return tokens




######################### Parsing validation #######################


def decompose(expression):
    list_of_sub_expressions = []
    
    if type(expression) == tuple:
        return expression

    i = 0
    while i < len(expression):    
        if expression[i][1] == 'and' or expression[i][1] == 'or' or expression[i][1] == 'not':
            list_of_sub_expressions.append(expression[i])
            i += 1

        elif expression[i][0] == 'ID' or expression[i][1] == 'True' or expression[i][1] == 'False':
            list_of_sub_expressions.append(expression[i])
            i += 1

        elif expression[i] == ('OP', '('):
            sub_expression = []
            i += 1
            open = 1
            while open > 0 and i < len(expression):
                if expression[i] == ('OP', '('):
                    open += 1
                elif expression[i] == ('OP', ')'):
                    open -= 1
                if open > 0:
                    sub_expression.append(expression[i])
                i += 1

            list_of_sub_expressions.append(sub_expression)
    
    return list_of_sub_expressions



class ParsingError(Exception):
    pass

class ExpressionError(Exception):
    pass


def check_subexpression_validity(expression):
    sub_expression = decompose(expression)
    if sub_expression != expression:
        if len(sub_expression) > 1:
            i = 0
            if sub_expression[i] == ('KEYWORD', 'not'):
                check_subexpression_validity(sub_expression[i+1])
            else:
                exp_type = sub_expression[i+1][1]
                while i < len(sub_expression):
                    if i%2 == 0:
                        check_subexpression_validity(sub_expression[i])
                        i += 1
                    else:
                        if sub_expression[i][1] != exp_type:
                            raise ExpressionError(f"The expression cannot be a mix of OR and AND.")
                        i += 1



def is_expression_valid(expression):
    
    if expression[-1][1] == 'not' or expression[-1][1] == 'and' or expression[-1][1] == 'or':
        raise ExpressionError(f"The last element of the expression is not valid.")

    stack = 0
    for i in range(len(expression)):
        if expression[i][1] == '(':
            stack += 1
        if expression[i][1] == ')':
            stack -= 1
        if stack < 0:
            raise ExpressionError(f"There are more closed parenthesis than opened")
        
    for i in range(len(expression)-1):
        if expression[i][1] == '(':
            if expression[i+1][1] == ')':
                raise ExpressionError(f"This is invalid: '()'")
            elif expression[i+1][1] == 'and':
                raise ExpressionError(f"This is invalid: '(and'")
            elif expression[i+1][1] == 'or':
                raise ExpressionError(f"This is invalid: '(or'")
            
        elif expression[i][1] == ')':
            if expression[i+1][0] == 'ID':
                raise ExpressionError(f"This is invalid: '){expression[i+1][1]}'")
            elif expression[i+1][1] == 'not':
                raise ExpressionError(f"This is invalid: ')not'")
            
        elif expression[i][0] == 'ID' or expression[i][0] == True or expression[i][0] == False:
            if expression[i+1][0] == 'ID' or expression[i+1][0] == True or expression[i+1][0] == False:
                raise ExpressionError(f"You cannot have two IDs after another")
            elif expression[i+1][1] == '(':
                raise ExpressionError(f"This is invalid: 'ID  ('")
            elif expression[i+1][1] == 'not':
                raise ExpressionError(f"This is invalid: 'ID not'")
            
        elif expression[i][1] == 'and' or expression[i][1] == 'or':
            if expression[i+1][1] == 'and' or expression[i+1][1] == 'or':
                raise ExpressionError(f"You cannot have two a combination of 'and' and 'or' next to each other.")
            elif expression[i+1][1] == ')':
                raise ExpressionError(f"You cannot close a parenthesis after an 'and' or an 'or'.")
            elif expression[i+1][1] == 'not':
                raise ExpressionError(f"You cannot have 'and not' or 'or not'")
            
        elif expression[i][1] == 'not':
            if expression[i+1][1] == ')':
                raise ExpressionError(f"You cannot have 'not)'")
            elif expression[i+1][1] == 'not':
                raise ExpressionError(f"You cannot have 'not not'")
            elif expression[i+1][1] == ')':
                raise ExpressionError(f"You cannot have 'not)'")
            elif expression[i+1][1] == 'and':
                raise ExpressionError(f"You cannot have 'not and'")
            elif expression[i+1][1] == 'or':
                raise ExpressionError(f"You cannot have 'not or'")
            
    if stack>0:
        raise ExpressionError(f"There are {stack} unclosed parenthesis")
    
    check_subexpression_validity(expression)



def parsing_validation(tokens):
    variables = []
    identifiers = []
    expressions = {}

    declaring_variables = False
    assigning_identifier = False
    showing = False
    
    var_count = 0
    i = 0

    if tokens[-1] != ('OP', ';'):
        raise ParsingError(f"Last token should be ';' " )

    while i < len(tokens):
        #declaring variables
        if tokens[i] == ('KEYWORD', 'var'):
            declaring_variables = True
            i += 1

        while declaring_variables:
            if tokens[i][0] == 'ID':
                if tokens[i][1] in variables or tokens[i][1] in expressions:
                    raise ParsingError(f"Variable '{tokens[i][1]}' is declared multiple times.")
                variables.append(tokens[i][1])
                var_count += 1
                i += 1
                if var_count > 64:
                    raise ParsingError("Too many variables declared; maximum allowed is 64.")
            elif tokens[i] == ('OP', ';'):
                declaring_variables = False
                i += 1
            else:
                raise ParsingError(f"Expected ';' after variable declaration.")
        

        #assigning expressions
        if tokens[i][0] == 'ID':
            if tokens[i+1] == ('OP', '='):
                if tokens[i][1] in variables or tokens[i][1] in identifiers:
                    raise ParsingError(f"Identifier '{tokens[i][1]}' is assigned multiple times.")
                else:
                    assigning_identifier = True
                    identifier = tokens[i][1]
                    identifiers.append(identifier)
                    expressions[identifier] = None
                    expression = []
                    i += 2
            else:
                raise ParsingError(f"Expected '=' after starting assignment")
        
        while assigning_identifier:
            if tokens[i] == ('KEYWORD', 'show') or tokens[i] == ('KEYWORD', 'show_ones') or tokens[i] == ('KEYWORD', 'var') or tokens[i] == ('OP', '='):
                raise ParsingError(f"Improper type {tokens[i]} in assigning expression or you forgot a ';'")
            if tokens[i] == ('OP', ';'):
                assigning_identifier = False
                expressions[identifier] = expression
            else:
                if tokens[i][1] == identifier:
                    raise ParsingError(f"{tokens[i][1]} cannot be defined using itself.")

                if tokens[i][0] == 'ID' and tokens[i][1] not in variables and tokens[i][1] not in expressions and tokens[i][1] not in ['True', 'False']:
                    raise ParsingError(f"Identifier '{tokens[i][1]}' used in expression without prior declaration.")
                expression.append(tokens[i])
                i += 1

        is_expression_valid(expression)


        #show statement
        if tokens[i] == ('KEYWORD', 'show') or tokens[i] == ('KEYWORD', 'show_ones'):
            showing = True
            id_to_show = []
            i += 1
        
        
        while showing:
            if tokens[i] == ('OP', ';'):
                showing = False
                print('\n')

            elif tokens[i][0] == 'ID':
                if tokens[i][1] in expressions:
                    id_to_show.append(tokens[i][1])
                else:
                    raise ParsingError(f"'{tokens[i][1]}' is not defined but it's trying to be used in a show statement.")
                i += 1

            else:
                raise ParsingError(f"In a show statement 'ID' is expected, but got {tokens[i][0]} instead." )

        i += 1

    return




######################## Functions for building tree and evaluating ####################


class ASTNode:
    def __init__(self, value, children=None):
        self.value = value  # Can be 'and', 'or', 'not', a variable name, True, or False
        self.children = children if children is not None else []


    def evaluate(self, variable_values):
        if isinstance(self.value, bool):
            return self.value
        elif isinstance(self.value, str):
            if self.value in variable_values:
                return variable_values[self.value]
            elif self.value == 'not':
                return not self.children[0].evaluate(variable_values)
            elif self.value == 'and':
                for child in self.children:
                    if not child.evaluate(variable_values):
                        return False  # Short-circuit: if any child is False, the whole AND is False
                return True
            elif self.value == 'or':
                for child in self.children:
                    if child.evaluate(variable_values):
                        return True  # Short-circuit: if any child is True, the whole OR is True
                return False
            




def build_ast(tokens, trees):
    stack = []  # Stack to handle nested expressions
    current_node = None

    for token in tokens:
        if token[0] == 'OP':
            if token[1] == '(':
                # Start a new subexpression: push the current node onto the stack
                stack.append(current_node)
                current_node = None
            elif token[1] == ')':
                # End of subexpression: the current_node is now complete
                if stack:
                    parent = stack.pop()
                    if parent:
                        parent.children.append(current_node)
                        current_node = parent
        elif token[0] == 'KEYWORD':
            if token[1] in ('and', 'or'):
                # Handle 'and' and 'or' operators
                if current_node and current_node.value == token[1]:
                    continue  # If it's the same operator, don't create a new node
                else:
                    # Create a new 'and' or 'or' node
                    new_node = ASTNode(token[1])
                    if current_node:
                        # Attach the current node as a child of the new node
                        new_node.children.append(current_node)
                    current_node = new_node
            elif token[1] == 'not':
                # 'not' is a unary operator, so it should have exactly one child
                new_node = ASTNode('not')
                if current_node:
                    stack.append(current_node)  # Save the current context
                current_node = new_node  # Switch context to the new 'not' node
            elif token[1] in ('True', 'False'):
                # Handle 'True' and 'False' as boolean literals
                new_node = ASTNode(True if token[1] == 'True' else False)
                if current_node:
                    current_node.children.append(new_node)
                else:
                    current_node = new_node
        elif token[0] == 'ID':
            if token[1] in trees:
                # If the identifier is a previously defined expression, use its tree
                new_node = copy.deepcopy(trees[token[1]])
            else:
                # Otherwise, create a new node for the variable
                new_node = ASTNode(token[1])

            if current_node:
                # Append to the current 'and', 'or', or 'not' node
                current_node.children.append(new_node)
            else:
                current_node = new_node

    # If there's still a node on the stack after processing all tokens, it becomes the root
    while stack:
        parent = stack.pop()
        if parent:
            parent.children.append(current_node)
            current_node = parent

    return current_node







def evaluate_expression(ast, variable_values):
    return ast.evaluate(variable_values)




def parsing_with_tree(tokens):
    variables = []
    identifiers = []
    expressions = {}
    trees = {}

    declaring_variables = False
    assigning_identifier = False
    
    i = 0

    while i < len(tokens):
        #declaring variables
        if tokens[i] == ('KEYWORD', 'var'):
            declaring_variables = True
            i += 1

        while declaring_variables:
            if tokens[i][0] == 'ID':
                variables.append(tokens[i][1])
                i += 1
            elif tokens[i] == ('OP', ';'):
                declaring_variables = False
                i += 1
        

        #assigning expressions and constructing tree
        if tokens[i][0] == 'ID' and tokens[i+1] == ('OP', '='):
            assigning_identifier = True
            identifier = tokens[i][1]
            identifiers.append(identifier)
            expressions[identifier] = None
            expression = []
            i += 2
        
        while assigning_identifier:
            if tokens[i] == ('OP', ';'):
                assigning_identifier = False
                expressions[identifier] = expression
                trees[identifier] = build_ast(expression, trees)

            else:
                expression.append(tokens[i])
                i += 1


        i += 1

    return variables, identifiers, expressions, trees






###################### Functions for printing #####################





def binary_representation_and_dict(variables, k):
    n = len(variables)
    
    # Convert k to binary and pad it to length n
    binary_rep = bin(k)[2:].zfill(n)  # Get binary and remove '0b', then pad with zeros
    
    # Create the dictionary, with the first variable being the most significant bit
    binary_dict = {variables[i]: bool(int(binary_rep[i])) for i in range(n)}
    
    return binary_rep, binary_dict





def show_truth_table(id_to_show, variables, trees, show_ones=False):
    for i in range(2 ** len(variables)):

        results = []
        for id in id_to_show:
            binary_num, binary_dict = binary_representation_and_dict(variables, i)
            ast_root = trees[id]
            result = evaluate_expression(ast_root, binary_dict)
            results.append(int(result))

        all_zeros = all(x == 0 for x in results)
        results = ' '.join(map(str, results))

        if show_ones and not all_zeros:
            print(binary_num + '    ' + results)

        elif not show_ones:
            print(binary_num + '    ' + results) 

    return








def parsing_and_printing(tokens, trees):
    variables = []
    identifiers = []
    expressions = {}

    declaring_variables = False
    assigning_identifier = False
    showing = False
    
    i = 0

    while i < len(tokens):
        #declaring variables
        if tokens[i] == ('KEYWORD', 'var'):
            declaring_variables = True
            i += 1

        while declaring_variables:
            if tokens[i][0] == 'ID':
                variables.append(tokens[i][1])
                i += 1
            elif tokens[i] == ('OP', ';'):
                declaring_variables = False
                i += 1
        

        #assigning expressions and constructing tree
        if tokens[i][0] == 'ID' and tokens[i+1] == ('OP', '='):
            assigning_identifier = True
            identifier = tokens[i][1]
            identifiers.append(identifier)
            expressions[identifier] = None
            expression = []
            i += 2
        
        while assigning_identifier:
            if tokens[i] == ('OP', ';'):
                assigning_identifier = False
                expressions[identifier] = expression

            else:
                expression.append(tokens[i])
                i += 1



        #showing truth table
        if tokens[i] == ('KEYWORD', 'show'):
            showing = True
            id_to_show = []
            i += 1
        
        
        while showing:
            if tokens[i] == ('OP', ';'):
                show_truth_table(id_to_show, variables, trees, False)
                showing = False
                print('\n')

            else:
                id_to_show.append(tokens[i][1])
                i += 1


        #showing ones truth table
        if tokens[i] == ('KEYWORD', 'show_ones'):
            showing = True
            id_to_show = []
            i += 1
        
        
        while showing:
            if tokens[i] == ('OP', ';'):
                show_truth_table(id_to_show, variables, trees, True)
                showing = False
                print('\n')

            else:
                id_to_show.append(tokens[i][1])
                i += 1


        i += 1

    return









######################## Main function #############################


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 table.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]

    try:
        with open(input_file, 'r') as file:
            program = file.read()
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)

    tokens = tokenize(program)
    parsing_validation(tokens)
    variables, identifiers, expressions, trees = parsing_with_tree(tokens)

    parsing_and_printing(tokens, trees)

    


