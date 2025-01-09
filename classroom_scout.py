import os
import json
from bs4 import BeautifulSoup
from datetime import datetime
import shlex

CRN_INDEX = 1
SUBJ_INDEX = 2
CRSE_INDEX = 3
SEC_INDEX = 4
TYPE_INDEX = 5
DAYS_INDEX = 8
TIME_INDEX = 9
DATE_INDEX = 17
LOCATION_INDEX = 18
FIELD_COUNT = 20
DATE_RANGE_START = 0
DATE_RANGE_END = 1
DAYS_OF_WEEK = ["M", "T", "W", "R", "F"]
input_folder_name = "input"
database_name = "database.json"
year = datetime.now().year

def build_database():
    print("Updating or building database...")
    global input_folder_name
    global database_name
    global year
    # Read files in input folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(current_dir, input_folder_name)
    source = ""
    number_files_parsed = 0
    for file_name in os.listdir(input_folder):
        if file_name.endswith(".html") or file_name.endswith(".htm"):
            number_files_parsed += 1
            file_path = os.path.join(input_folder, file_name)
            with open(file_path, 'r', encoding='utf-8') as file:
                source += file.read()
                source += "\n"
    soup = BeautifulSoup(source, "html.parser")
    tables = soup.find_all("table", class_="datadisplaytable", summary="This layout table is used to present the sections found")
    if (number_files_parsed == 0):
        print("Database build failed: No input files were found")
        return
    # Collect rows from every table
    rows = []
    for table in tables:
        rows.extend(table.find_all('tr'))
    courses = {}
    current_module = None
    for row in rows:
        cells = row.find_all(['td', 'th'])
        cells_txt = [cell.get_text(strip=True) for cell in cells]
        # Skip incomplete rows and header rows
        if ((len(cells) != FIELD_COUNT) or
            (cells_txt[CRN_INDEX] == "CRN") or
            (cells_txt[DAYS_INDEX] == "TBA") or
            (cells_txt[TIME_INDEX] == "TBA") or
            (cells_txt[DATE_INDEX] == "TBA")
            ):
            continue
        # Row is assumed to describe meeting, so create meeting
        meeting = {
            "Days" : list(cells_txt[DAYS_INDEX]),
            "Start Time": cells_txt[TIME_INDEX].split("-")[0],
            "End Time": cells_txt[TIME_INDEX].split("-")[1],
            "Start Date": cells_txt[DATE_INDEX].split("-")[0] + "/" + str(year-2000),
            "End Date": cells_txt[DATE_INDEX].split("-")[1] + "/" + str(year-2000),
            "Location": cells_txt[LOCATION_INDEX]
        }
        # If row defines module, create module
        if (cells_txt[CRN_INDEX] != ""):
            meetings = []
            current_module = {
                "CRN": cells_txt[CRN_INDEX],
                "Section": cells_txt[SEC_INDEX],
                "Type": cells_txt[TYPE_INDEX],
                "Meetings": meetings
            }
            # Create new course if it doesn't already exist 
            course_code = cells_txt[SUBJ_INDEX] + cells_txt[CRSE_INDEX]
            if course_code not in courses:
                modules = []
                courses[course_code] = modules
            # Add module to course
            courses[course_code].append(current_module)
        # Add meeting to module
        current_module["Meetings"].append(meeting)
    # Write to JSON
    database_json = json.dumps(courses)
    database_path = os.path.join(current_dir, database_name)
    with open(database_path, "w") as json_file:
        json_file.write(database_json)
    print("Database updated or built in " + str(database_path))

def flatten_database():
    global database_name
    result = []
    with open(database_name, "r") as json_file:
        database = json.load(json_file)
        for course in database:
            for module in database[course]:
                for meeting in module["Meetings"]:
                    flattened_data = {"Course": course}
                    for data_item in module:
                        if (data_item == "Meetings"):
                            continue
                        flattened_data[data_item] = module[data_item]
                    for data_item in meeting:
                        flattened_data[data_item] = meeting[data_item]
                    result.append(flattened_data)
    return result

def parse_date(date_string):
    return datetime.strptime(date_string, "%m/%d/%y")

def parse_time(time_string):
    return datetime.strptime(time_string, "%I:%M %p")

def room_schedule(room, date_string):
    if not (room in get_room_list()):
        print("Room code not recognized.")
        return
    print("Schedule for " + room + " on " + date_string + ":")
    output_am = []
    output_pm = []
    date = None
    if (date_string == "today") or (date_string == "Today"):
        date = datetime.today()
    else:
        date = parse_date(date_string)
    for meeting in flatten_database():
        if room != meeting["Location"]:
            continue
        if DAYS_OF_WEEK[date.weekday()] not in meeting["Days"]:
            continue
        if date < datetime.strptime(meeting["Start Date"], "%m/%d/%y"):
            continue
        if date > datetime.strptime(meeting["End Date"], "%m/%d/%y"):
            continue
        line = meeting["Start Time"] + "-" + meeting["End Time"] + " " + meeting["Course"] + " " + meeting["Type"]
        if ("am" in meeting["Start Time"]):
            output_am.append(line)
        else:
            output_pm.append(line)
    output_am.sort()
    output_pm.sort()
    if (len(output_am) == 0) and (len(output_pm) == 0):
        print("No classes scheduled.")
        return
    for line in output_am:
        print(line)
    for line in output_pm:
        print(line)

def print_nicely(list):
    for a,b,c in zip(list[::3],list[1::3],list[2::3]):
        print('{:<30}{:<30}{:<}'.format(a,b,c))

def get_room_list():
    rooms = []
    for meeting in flatten_database():
        if (meeting["Location"] not in rooms):
            rooms.append(meeting["Location"])
    return rooms

def find_room(date_string, start_time_string, end_time_string):
    rooms = get_room_list()
    if (date_string == "today") or (date_string == "Today"):
        date = datetime.today()
    else:
        date = parse_date(date_string)
    start_time = parse_time(start_time_string)
    end_time = parse_time(end_time_string)
    for meeting in flatten_database():
        if DAYS_OF_WEEK[date.weekday()] not in meeting["Days"]:
            continue
        if date < datetime.strptime(meeting["Start Date"], "%m/%d/%y"):
            continue
        if date > datetime.strptime(meeting["End Date"], "%m/%d/%y"):
            continue
        if (start_time < parse_time(meeting["Start Time"])) and (end_time < parse_time(meeting["Start Time"])):
            continue
        if (start_time > parse_time(meeting["End Time"])) and (end_time > parse_time(meeting["End Time"])):
            continue
        if meeting["Location"] in rooms:
            rooms.remove(meeting["Location"])
    if (len(rooms) == 0):
        print("No rooms found.")
        return
    rooms.sort()
    print("Rooms without classes scheduled on " + date_string + " from " + start_time_string + " to " + end_time_string + ":")
    print_nicely(rooms)

def print_room_list():
    print("All room codes in database:")
    list = get_room_list()
    list.sort()
    print_nicely(list)

def main():
    while True:
        print("\nClassroom Scout Commands:")
        print("1. build - Update or build the database")
        print("2. list - List all room codes")
        print('3. schedule "ROOM CODE" "MM/DD/YY" - Get schedule for a room')
        print('4. find "MM/DD/YY" "HH:MM am" "HH:MM pm" - Find all rooms without classes scheduled')
        print("5. exit - Exit program")
        
        try:
            command = shlex.split(input("\nEnter command: "))
        except ValueError as e:
            print("Error parsing command: Make sure quotes are matched")
            continue
            
        if not command:
            continue
            
        if command[0] == 'build':
            build_database()
        elif command[0] == 'list':
            print_room_list()
        elif command[0] == 'schedule':
            if len(command) != 3:
                print('Usage: schedule "ROOM CODE" "MM/DD/YY"')
                print('Example: schedule "ENGTR 0100" "1/8/25"')
                continue
            room_schedule(command[1], command[2])
        elif command[0] == 'find':
            if len(command) != 4:
                print('Usage: find "MM/DD/YY" "HH:MM AM" "HH:MM AM"')
                print('Example: find "1/8/25" "10:00 AM" "11:30 AM"')
                continue
            find_room(command[1], command[2], command[3])
        elif command[0] in ['exit', 'quit', '5']:
            print("Program exit.")
            break
        else:
            print("Unknown command.")

if __name__ == '__main__':
    main()