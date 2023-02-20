import pyswip
from pyswip.prolog import Prolog
from pyswip.easy import *
from tkinter import *
from tkinter import Label, Button, Tk, Frame, simpledialog
import tempfile
import os
import pandas as pd

KB = """
:- dynamic known/3, known/2, multivalued/1. % dynamic predicates
:- discontiguous known/3, known/2, multivalued/1, budget/2, cuisine/2, dietary_restrictions/2, distance/2, has/1, include/1, is_open_at/3, is_open_on/2, needs_reservation/1, rating/2, res_hall/2, time/1, day/1, open_hours/2, open_days/2, ask_input/2, ask_menu/3, ask_multiple/3, all_restrictions/1, cuisines/1, res_halls/1.

recommendation(X) :- findall(T, match(T), Y), sort(Y, Sorted), member(X, Sorted).

match(Restaurant) :-
day(Day), is_open_on(Restaurant, Day),
time(Time), is_open_at(Restaurant, Day, Time),
rating(Rating), rating(Restaurant, ResRating), ResRating >= Rating,
res_hall(Res), res_hall(Restaurant, ResHall), ResHall = Res,
distance(Distance), distance(Restaurant, ResDistance), ResDistance =< Distance,
(\+has(dietary_restrictions); (has(dietary_restrictions), dietary_restrictions(Restrictions), dietary_restrictions(Restaurant, ResRestrictions), subset(Restrictions, ResRestrictions))),
(\+has(cuisine_preference); (has(cuisine_preference), cuisine(Cuisine), cuisine(Restaurant, ResCuisine), member(ResCuisine, Cuisine))),
budget(Budget), budget(Restaurant, ResBudget), ResBudget =< Budget,
(\+needs_reservation(Restaurant); (needs_reservation(Restaurant), include(reservations))).

% Determine if the restaurant is open based on opening and closing times
is_open_on(Restaurant, Day) :- open_days(Restaurant, OpenDays), member(Day, OpenDays).
is_open_at(Restaurant, Day, Time) :- open_days(Restaurant, OpenDays), open_hours(Restaurant, OpenHours), nth0(Index, OpenDays, Day), nth0(Index, OpenHours, DayPeriods), member(Period, DayPeriods), nth0(0, Period, Start), Time >= Start, nth0(1, Period, End), Time =< End.

% Prompting the user:
day(X) :- ask_menu('What day is it today?', X, [monday, tuesday, wednesday, thursday, friday, saturday, sunday]).
time(X) :- ask_input('What time would you like to eat? Enter a time in military format (e.g. 1500)', X), !.
rating(X) :- ask_input('What is your preferred restaurant rating out of 5?', X), !.
res_hall(X) :- res_halls(ResHalls), ask_menu('What is your Residence hall?', X, ResHalls), !.
distance(X) :- ask_input('How many meters would you like to travel to the restaurant?', X), !.
has(dietary_restrictions) :- ask_menu('Do you have any dietary restrictions?', X, [yes, no]), X = yes.
dietary_restrictions(X) :- has(dietary_restrictions), all_restrictions(Restrictions), ask_multiple('Select all the dietary restrictions that apply to you.', X, Restrictions).
has(cuisine_preference) :- ask_menu('Do you have any type of cuisine preference?', X, [yes, no]), X = yes.
cuisine(X) :- has(cuisine_preference), cuisines(Cuisines), ask_multiple('What cuisines are you craving? Select all that apply.', X, Cuisines).
budget(X) :- ask_input('What is your preferred budget? Please enter a valid budget number from 1 (least expensive) to 3 (pricy)', X), !.
include(reservations) :- ask_menu('Do you want to include restaurants that require reservations?', X, [yes, no]), X = yes.

% Asking clauses

ask_input(A, V) :-
known(A, V),
!.

% Menu option asking clauses
ask_menu(A, V, _):-
known(A, V),
!.

ask_multiple(A, V, _):-
known(A, V),
!.

% If not multivalued, and already known to be something else, don't ask again for a different value.

ask_input(A, V):-
known(A, V2),
V \== V2,
!, fail.

ask_input(A, Y):-
read_val(A,Y),
asserta(known(A, Y)),
Y \== cancel.

ask_multiple(A, Y, MenuList):-
read_py_multiple(A, Y, MenuList),
assertz(known(A, Y)),
Y \== cancel.


ask_menu(A, V, _):-
known(A, V2), % If already known, don't ask again for a different value.
V \== V2,
!,
fail.

ask_menu(A, V, MenuList) :-
 read_py_menu(A, X, MenuList),
 (X \== cancel),
 check(X, A, V, MenuList),
 asserta( known(A, V) ).
 
% Checking if the answer is valid item in the menu list 
check(X, _, V, MenuList) :-
 member(X, MenuList),
 X = V,
 !.
 
check(X, A, V, MenuList) :-
 error_message(X),
 ask_menu(A, V, MenuList).
"""

# insert data from the csv file into the KB
df = pd.read_csv('../CS152 LBA - Restaurant data collection.csv')
days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
for i in range(len(df)):
    name = str(df['Restaurant Name'][i])
    open_days = [day.lower() for day in days if df[day][i] != "closed"]
    open_hours = []
    for day in days:
        if df[day][i] != "closed":
            day_periods = []
            periods = df[day][i].split(';')
            for period in periods:
                day_periods.append([int(time.replace(':', '')) for time in period.split('-')])
            open_hours.append(day_periods)
    if df['Dietary restrictions'][i] == 'None':
        dietary_restrictions = ""
    else:
        dietary_restrictions = f"dietary_restrictions('{name}', X) :- X = %s." % (str([restriction.lower() for restriction in df["Dietary restrictions"][i].split(", ")]))

    KB += f"""
open_days('{name}', X) :- X = {str(open_days)}.
open_hours('{name}', X) :- X = {str(open_hours).replace("'", "")}.
rating('{name}', X) :- X = {df['Rating'][i]}.
res_hall('{name}', X) :- X = '{df['Res hall'][i].lower()}'.
distance('{name}', X) :- X = {int(df['Distance'][i].replace('m', ''))}.
{dietary_restrictions}
cuisine('{name}', X) :- X = '{df['Cuisine'][i].lower()}'.
budget('{name}', X) :- X = {len(df['Budget'][i])}.
{f"needs_reservation('{name}')." if df['Needs reservation'][i] == 'Yes'  else ""}
"""

KB += f"""
res_halls(X) :- X = {str([res_hall.lower() for res_hall in df['Res hall'].unique()])}.
cuisines(X) :- X = {str([cuisine.lower() for cuisine in df['Cuisine'].unique()])}.
all_restrictions(X) :- X = {str([restriction.lower() for restriction in df['Dietary restrictions'].apply(lambda x: x.split(', ')).explode().unique() if restriction != 'None'])}.
"""
print(KB)


prolog = Prolog()

class app():
    
  def __init__(self, master):
    frame = Frame(master)
    frame.pack(fill=BOTH, expand=True)

    canvas = Canvas(frame, bg='white')
    scrollbar = Scrollbar(canvas, orient="vertical", command=canvas.yview)
    scrollable_frame = Frame(canvas)
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    self.chatWindow = Label(scrollable_frame, text="Get personalized restaurant recommendations near your residence hall\n", bd=1, bg='white', fg='black', font="Helvetica 12", justify=LEFT, anchor=NW)
    self.chatWindow.pack(fill=BOTH, expand=True)

    self.Button = Button(frame, text="Start chatting", fg='white', bg='blue', activebackground='red', command=lambda: queryGenerator(), height=5)
    self.Button.pack(fill=X, expand=False, side=BOTTOM)
    frame.pack(fill=BOTH, expand=True)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    
    

def user_response(response: str) -> None:
    """
    Prints the input response to the GUI and returns True to Prolog
    and prepending USER to show that it is the user talking
    """
    app.chatWindow['text'] += f'YOU: {response}\n'
    print(response)
    return True

def system_response(response: str) -> None:
    """
    Prints the input response to the GUI and returns True to Prolog
    and prepending SYSTEM to show that it is the system talking
    """
    app.chatWindow['text'] += f'SYSTEM: {response}'
    print(response)
    return True

def error_message(response: str) -> None:
    """
    Prints the input response to the GUI and returns True to Prolog
    and prepending ERROR to show that it is an error message
    """
    app.chatWindow['text'] += f'SYSTEM: {response} is not a valid option. Please try again.\n'
    print(str(response) + " is not a valid option. Please try again.")
    return True


def queryGenerator():
    
    call(retractall(menu_known))
    call(retractall(val_known))

    # app.chatWindow['text'] = "="*70 + "\n" 

    # q = list(prolog.query("res_hall(X), res_hall(Restaurant, ResHall), ResHall = Res.")) # prolog query
    q = list(prolog.query("recommendation(X), rating(X, Rating), distance(X, Distance), budget(X, Budget), cuisine(X, Cuisine), (dietary_restrictions(X, DietaryRestrictions) ; (\+dietary_restrictions(X, _), DietaryRestrictions = none)), ((needs_reservation(X), NeedsReservation = 'Yes') ; (\+needs_reservation(X),NeedsReservation = 'No')).")) # prolog query
    print(q)

    for v in q:
        app.chatWindow['text'] += f"RECOMMENDATION ==> {str(v['X'])}\n"
        app.chatWindow['text'] += f"Rating: {str(v['Rating'])} / 5\n"
        app.chatWindow['text'] += f"Distance: {str(v['Distance'])}m\n"
        app.chatWindow['text'] += f"Budget: {str(v['Budget'])}\n"
        app.chatWindow['text'] += f"Cuisine: {str(v['Cuisine'])}\n"
        app.chatWindow['text'] += f"Dietary Restrictions: {', '.join([str(x) for x in v['DietaryRestrictions']]) if v['DietaryRestrictions'] != 'none' else 'None'}\n"
        app.chatWindow['text'] += f"Needs Reservation: {str(v['NeedsReservation'])}\n\n"


    app.Button.configure(text="Run again")

system_response.arity = 1
user_response.arity = 1
error_message.arity = 1

def read_py_menu(A: Atom, Y: Variable, MenuList: list) -> bool:
    """
    Based on menu, asks the user for input.
    -A: The askable
    -Y: The answer
    -MenuList: The options in the menu

    -returns True if Y is a Prolog variable and False otherwise.
    """
    if isinstance(Y, pyswip.easy.Variable):
        question = "" + str(A) + "\n"
        for i, x in enumerate(MenuList):
            question += "\t" + str(i+1) + " .  " + str(x) + "\n"
        response = get_menu_input(question, MenuList)
        if response == None:
            response = "cancel"
            # user_response(response)
            # Y.unify(response)
            # return False
        user_response(response)
        Y.unify(response)
        return True
    else:
        return False

def get_menu_input(question: str, MenuList: list) -> str:
    """
    Identifies the user input - user can either choose a number or write some text.

    - MenuList: The options that the user needs to choose from. They are stored as Prolog Atoms.
    - lst_lcs: The options stored in a list of strings that Python can interpret.

    - returns the user choice as a string.
    """
    system_response(question)
    from_user = simpledialog.askstring("Input", question,
                                       parent=root)
    try:
        response_int = int(from_user)
        response = str(MenuList[response_int-1])
    except:
        if from_user == None:
            return None
        response = from_user.lower()
    return response

multiple_response = []
def read_py_multiple(A: Atom, Y: Variable, MenuList: list) -> bool:
    """
    Based on menu, asks the user for input.
    -A: The askable
    -Y: The answer
    -MenuList: The options in the menu

    -returns True if Y is a Prolog variable and False otherwise.
    """
    if isinstance(Y, pyswip.easy.Variable):
        question = str(A) + "\n"
        response = get_multiple_input(question, MenuList)
        if response == None:
            response = "cancel"
            # user_response(response)
            # Y.unify(response)
            # return False
        final_response = ", ".join(response)
        user_response(final_response)
        Y.unify(response)

        return True
    else:
        return False

def get_multiple_input(question: str, MenuList: list) -> str:
    """
    Identifies the user input - user can either choose a number or write some text.

    - MenuList: The options that the user needs to choose from. They are stored as Prolog Atoms.
    - lst_lcs: The options stored in a list of strings that Python can interpret.

    - returns the user choice as a string.
    """
    system_response(question)

    window = Tk()
    window.title('Multiple selection')

    yscrollbar = Scrollbar(window)
    yscrollbar.pack(side = RIGHT, fill = Y)
    
    label = Label(window,
                text = question,
                font = ("Helvetica", 10))
    label.pack()
    list = Listbox(window, selectmode = "multiple", 
                yscrollcommand = yscrollbar.set)
    list.pack(padx = 10, pady = 10,
          expand = YES, fill = "both")

    for i in range(len(MenuList)):
        list.insert(END, MenuList[i])

    yscrollbar.config(command = list.yview)

    response = []
    def get():
        selection = list.curselection()
        for i in selection:
            response.append(list.get(i))
        
        window.quit()
        print(response)
        window.destroy()

    button = Button(window, text = "OK", command = get)
    button.pack(pady = 10)

    window.mainloop()

    return response

def read_val(A: Atom, Y: Variable) -> bool:
    """
    Asks the user for input.
    -A: The askable
    -Y: The answer

    -returns True if Y is a Prolog variable and False otherwise.
    """
    if isinstance(Y, pyswip.easy.Variable):
        question = "" + str(A) + "\n"
        response = get_input(question)
        if response == None:
            response = "cancel"
            # return False
        user_response(response)
        Y.unify(response)
        return True
    else:
        return False

def get_input(question: str) -> str:
    """
    Identifies the user input - user can either choose a number or write some text.

    - MenuList: The options that the user needs to choose from. They are stored as Prolog Atoms.
    - lst_lcs: The options stored in a list of strings that Python can interpret.

    - returns the user choice as a string.
    """
    system_response(question)
    from_user = simpledialog.askstring("Input", question,
                                       parent=root)
    try:
        response = int(from_user)
    except:
        try:
            response = float(from_user)
        except:
            if from_user == None:
                return None
            response = from_user.lower()

    return response


retractall = Functor("retractall")
menu_known = Functor("known",3)
val_known = Functor("known",2)

read_py_menu.arity = 3
read_val.arity = 2
read_py_multiple.arity = 3

registerForeign(read_py_menu)
registerForeign(read_val)
registerForeign(read_py_multiple)
registerForeign(system_response)
registerForeign(user_response)
registerForeign(error_message)

# Create a temporary file with the KB in it
(FD, name) = tempfile.mkstemp(suffix='.pl', text = True)
with os.fdopen(FD, "w") as text_file:
    text_file.write(KB)
# try:
#     prolog.consult(name) # open the KB for consulting
# except prolog.PrologError:
name = name.replace("\\", "/") # Windows fix
prolog.consult(name) # open the KB for consulting
os.unlink(name) # Remove the temporary file


root = Tk()
root.geometry("820x600")
root.resizable(1, 1)
root.config(bg='white')
app = app(root)
root.title("Restaurant Recommendation Chatbot")
root.mainloop()
