import json
from tkinter import *
from tkinter.filedialog import askopenfile

player_displayed = False

def display_player(event):
    global player_displayed

    def get_all():
        global player_displayed
        data["players"][index][4] = [i.get() for i in capacities] + [player[4][5]] + [i.get() for i in miscellaneous]
        with open(filename, "w") as file:
            file.write(json.dumps(data, indent=4))
        player_displayed = False
        frame.destroy()

    if player_displayed: return 
    player_displayed = True
    index = player_list.curselection()[0]
    player = data["players"][index]

    frame = LabelFrame(window, text=f"{player[1]} — {player[2]}")
    frame.pack(fill="both", expand="yes", padx=2, pady=2)

    capacity = LabelFrame(frame, text="Capacités", relief="sunken")
    capacity.pack(fill="both", expand="yes", padx=2, pady=2, side="left")

    misc = LabelFrame(frame, text="Divers", relief="sunken")
    misc.pack(fill="both", expand="yes", padx=2, pady=2)

    capacities = [IntVar() for _ in range(5)]
    for i in range(5):
        capacities[i].set(player[4][i])
        Label(capacity, text=("Courage", "Force", "Habileté", "Rapidité", "Intelligence")[i]).pack()
        Spinbox(capacity, textvariable=capacities[i], from_=0, to=100000).pack()

    miscellaneous = [IntVar() for _ in range(3)]
    for i in range(3):
        miscellaneous[i].set(player[4][6 + i])
        Label(misc, text=("Vie", "Mana", "Argent")[i]).pack()
        Spinbox(misc, textvariable=miscellaneous[i], from_=0, to=100000).pack()

    button = Button(frame, text="Valider", command=get_all).pack()

    

# Get the savefile
file = askopenfile(filetypes=[("json", "*.json")])
filename = file.name
file.close()
with open(filename, "r") as file:
    data = json.loads(file.read())


# Display players
window = Tk()

player_list = Listbox(window)
for index, player in enumerate(data["players"]):
    player_list.insert(index, player[1])
player_list.pack(side="left")

player_list.bind("<<ListboxSelect>>", display_player)

window.mainloop()