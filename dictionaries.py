## This file contains tool descriptions, query parameters, and other dictionaries that are needed by Deepseek as reference
departments = ['Top Management',
            'Manufacturing', 'Quality Regulatory Affairs & EHS',
            'Business Development', 'HR & Admin',
            'Supply Chain Management', 'Facilities & Maintenance',
            'Information Technology', 'Research & Development',
            'Accounting', 'Finance & Administration']

dept_alias = {'Quality Regulatory Affairs & EHS': ['QA', 'Quality Affairs'],
             'HR & Admin': ['HR', 'Human Resources'],
             'Supply Chain Management': ['Supply Chain', 'Logistics'],
             'Information Technology': ['IT'],
             'Research & Development': ['Research', 'R&D'],
             'Finance & Administration': ['Finance', 'Budgeting']}

default_tools = [
    {
        'name': 'get_past_conversations',
        'description': 'retrieves the last 5 exchanges between the user and Abigail'
    },
    {
        'name': 'clarify_user',
        'description': 'asks the user for additional information',
        'arguments': ['message_to_user']
    }
]

empdata_tools = [
    {
        'name': 'show_employee_list',
        'description': 'list of employees with their ID number, department, and job title'
    },
    {
        'name': 'show_department_list',
        'description': 'list of departments'
    },
    {
        'name': 'raw_attendance',
        'description': 'retrieve attendance logs for a person and date',
        'arguments': ['employee_name', 'employee_num', 'department', 'date']
    },
    {
        'name': 'dept_turnout',
        'description': 'count of present and total employees under a department for a given date',
        'arguments': ['department', 'date']
    }
]

opact_tools = [
    {
        'name': 'operator_output',
        'description': 'get the output, target time, and utilization rate per assigned station of an operator',
        'arguments': ['date', 'employee_name', 'employee_num', 'customer', 'model', 'station']
    },
    {
        'name': 'show_allowed_stations',
        'description': 'list of stations an employee is qualified to operate in',
        'arguments': ['employee_name', 'employee_num']
    },
    {
        'name': 'show_target_time',
        'description': 'list the standard target times for each station of a model that operators must reach',
        'arguments': ['customer', 'model', 'station']
    }
]

kts_tools = [
    {
        'name': 'station_yield',
        'description': "outputs a csv file containing raw data of a model's yield per given station",
        'arguments': ['customer', 'model', 'date']
    },
    {
        'name': 'get_wip',
        'description': 'quantity of units that are work-in-progress per given station of a model',
        'arguments': ['customer', 'model', 'date']
    },
    {
        'name': 'failure_details',
        'description': 'quantity and details about failed units of a given model',
        'arguments': ['customer', 'model', 'date']
    },
    {
        'name':'serial_query',
        'description': 'look for the model of a unit with the given serial number',
        'arguments': ['serial_number']
    },
    {
        'name': 'show_process_flow',
        'description': 'list of stations under a certain model stored as table columns',
        'arguments': ['customer', 'model']
    },
    {
        'name': 'show_purchase_orders',
        'description': 'list of purchase orders for a model',
        'arguments': ['customer', 'model']
    },
    {
        'name': 'show_running_models',
        'description': 'summary of models that are currently in production',
        'arguments': ['date']
    }
]

scopes_list = [
    {
        'query_type': 'employee_data',
        'description': 'to know employee data such as name, employee number, department, job title, or attendance',
        'tools': [tool['name'] for tool in empdata_tools],
        'examples': ["i would like to see the attendance of bryan last week", "what is ranbill's department?", "how many Business Development employees are present?"]
    },
    {
        'query_type': 'operator_data',
        'description': 'to get activity details of operators, such as their assigned stations, output, cycle time, target time, status, and utilization rate',
        'tools': [tool['name'] for tool in opact_tools],
        'examples': ["what is Marga doing now?", "which operator among those stationed at Lasermarking have the best cycle time?"]
    },
    {
        'query_type': 'production_data',
        'description': 'to fetch records from the database regarding the manufactured units of the company',
        'tools': [tool['name'] for tool in kts_tools],
        'examples': ["can i see the wip for templogger?", "what are the common fail reasons for nanoirtag at progtest station?", "i need csv file for ledtech lightboardl"]
    },
    {
        'query_type': 'external',
        'description': 'query is not related to company internal data',
        'tools': [],
        'examples': ["banana bread recipe", "what is the standard model?", "which country has a capital of Manila?"]
    }
]