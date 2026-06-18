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
        'parameters': ['message_to_user']
    }
]

# no parameters needed
level_0_tools = [
    # employee info
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
        'description': 'retrieve attendance logs for a given person and date',
        'parameters': ['employee_name OR employee_num OR department', 'date']
    },
    {
        'name': 'dept_turnout',
        'description': 'count of present and total employees under a department for a given date',
        'parameters': ['department', 'date']
    },
    # kts data
    {
        'name': 'show_running_models',
        'description': 'list of current customers and their models in production'
    },
    {
        'name': 'serial_query',
        'description': 'find the model and station progress of a unit given its serial number',
        'parameters': ['serial_num']
    }
]

# need parameters from level 0
level_1_tools = [
    # employee info
    
    # operator activity
    {
        'name': 'operator_output',
        'description': 'get the output, target time, and utilization rate per assigned station of an operator',
        'parameters': ['date', 'employee_name OR employee_num', 'customer', 'model', 'station']
    },
    {
        'name': 'show_allowed_stations',
        'description': 'list of stations an employee is qualified to operate in',
        'parameters': ['employee_name OR employee_num']
    },
    # kts data
    {
        'name': 'show_process_flow',
        'description': 'list of manufacturing stations of a given model',
        'parameters': ['customer', 'model']
    },
    {
        'name': 'show_purchase_orders',
        'description': 'list of purchase orders of a given model',
        'parameters': ['customer', 'model']
    }
]

# need parameters from level 1
level_2_tools = [
    # operator activity
    {
        'name': 'show_target_time',
        'description': 'list the standard target times for each station of a model that operators must reach',
        'parameters': ['customer', 'model', 'station']
    },
    # kts data
    {
        'name': 'get_wip',
        'description': 'quantity of units that are work-in-progress per given station of a model',
        'parameters': ['date', 'customer', 'model', 'station', 'PO_num']
    },
    {
        'name': 'station_yield',
        'description': 'output a csv file about the yield summary of a model per given station',
        'parameters': ['date', 'customer', 'model', 'station', 'PO_num']
    },
    {
        'name': 'failure_details',
        'description': 'quantity and details about failed units of a given model',
        'parameters': ['date', 'customer', 'model', 'station', 'PO_num']
    }
]

empdata_tools = [
    {
        'name': 'basic_info',
        'description': 'provide employee details such as name, employee number, department, and job title',
        'parameters': ['employee_name', 'employee_num'],
        'required': ['employee_name OR employee_num']
    },
    {
        'name': 'raw_attendance',
        'description': 'retrieve daily attendance logs for a person',
        'parameters': ['employee_name', 'employee_num', 'department', 'date'],
        'required': ['employee_name OR employee_num OR department', 'date']
    },
    {
        'name': 'dept_turnout',
        'description': 'percentage of present employees under a given department',
        'parameters': ['department', 'date'],
        'required': ['department', 'date']
    }
]

opact_tools = [
    {
        'name': 'allowed_stations',
        'description': 'list of stations that an employee is qualified to operate',
        'parameters': ['employee_name', 'employee_num']
    },
    {
        'name': 'activity_details',
        'description': 'operator details regarding their output, cycle time, and utilization rate at their stations',
        'parameters': ['date', 'employee_name', 'employee_num', 'customer', 'model', 'station']
    },
    {
        'name': 'compare_to_target',
        'description': 'compare the current cycle time of an operator to the target cycle time in the database',
        'parameters': ['employee_name', 'employee_num', 'date']
    }
]

kts_tools = [
    {
        'name': 'station_yield',
        'description': 'output a csv file about the yield summary of a model per given station',
        'parameters': ['customer', 'model', 'PO_number', 'stations', 'date']
    },
    {
        'name': 'get_wip',
        'description': 'quantity of units that are work-in-progress per given station of a model',
        'parameters': ['customer', 'model', 'PO_number', 'stations', 'date']
    },
    {
        'name': 'failure_details',
        'description': 'quantity and details about failed units of a given model',
        'parameters': ['customer', 'model', 'PO_number', 'stations', 'date']
    },
    {
        'name':'serial_query',
        'description': 'look for the model of a unit with the given serial number',
        'parameters': ['serial_number']
    },
    {
        'name': 'show_process_flow',
        'description': 'list of stations under a certain model stored as table columns',
        'parameters': ['customer', 'model']
    },
    {
        'name': 'show_purchase_orders',
        'description': 'list of purchase orders for a model',
        'parameters': ['customer', 'model']
    },
    {
        'name': 'show_running_models',
        'description': 'summary of models that are currently in production',
        'parameters': ['date']
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