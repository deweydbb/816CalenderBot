# do not change (for internal use of the program to map numbers to days)
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]



### START OF CONFIG ###

# Can find in the URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}/
SHEET_ID="1_qWl72k-m8rl9aYLkcvEc1tzHtNEU-Dki0gAdRTIuj0"
# must be of the form https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit
SHEET_URL=f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

# text people can put after their name to indicate to the bot they are keyholder
KEYHOLDER_MARKS=['🔑', 'keyholder']

# Days where the shop is open
SHIFT_DAYS = ['Monday', 'Thursday', 'Saturday']
# day of the week mapped to the slack channel to send the message in
# channel format is #{name of channel}
SHIFT_DAY_TO_CHANNEL = {
    'Monday': '#bot-tester',
    'Thursday': '#bot-tester',
    'Saturday': '#bot-tester'
}
if set(SHIFT_DAY_TO_CHANNEL.keys()) != set(SHIFT_DAYS):
    raise KeyError("SHIFT_DAYS and SHIFT_DAY_TO_CHANNEL must have the same days") 



# How many days out should the low volunteer warning and no keyholder warning be sent 
SHIFT_VOLUNTEER_WARNING_DAYS = [6, 3, 0]
# How many days out should the special notes for shift be sent out. 
SHIFT_SPECIAL_NOTES_DAYS = [0]

# if under number of volunteers signed up for shift, send warning
VOLUNTEER_THRESHOLD = 3