# Question list (coverage checklist)

The profile chat uses this to see what is still unknown. It is **not a script**: the agent asks in any order, skips what a reply already answered, and confirms researched facts instead of asking from scratch. `req` = required before `in_review`. `owner` = the owner must confirm if someone else answered. Add rows as new needs appear; never delete, mark SUPERSEDED.

| Field id | Question (intent) | req | owner | Unlocks |
|---|---|---|---|---|
| business.trading_name | Name guests know the business by | yes | | |
| business.location_note | Where guests arrive, parking, how to find it | yes | | |
| business.languages | Languages used with guests | | | |
| business.booking_today | How guests book today (phone, chat, walk-in, spreadsheet, platform) | yes | | |
| tours.list | Which tours are offered | yes | | tours.<id>.* |
| tours.<id>.duration_min | How long each tour runs | yes | | |
| tours.<id>.capacity_per_slot | Most guests per slot | yes | yes | |
| tours.<id>.min_age | Minimum age, if any | | | |
| tours.<id>.season | When it runs (all year, a season, school holidays) | yes | | |
| tours.<id>.slot_times | Start times per day and days of the week | yes | | |
| tours.<id>.outdoor | Is it outdoors (weather rule applies) | yes | | |
| policies.group_size | What counts as a group | yes | yes | policies.group_deposit |
| policies.group_deposit | Deposit for groups: how much and by when | yes | yes | |
| policies.cancellation_guest | Refund when a guest cancels, by notice period | yes | yes | |
| policies.cancellation_farm | What guests get when the operator cancels | yes | yes | |
| policies.weather | Who closes a slot for weather, and how much notice | yes | | |
| policies.closures | Closed days or seasons | yes | | |
| policies.waivers | Waivers or guardian forms needed | | | |
| policies.sales_tax_registered | Is sales tax charged | yes | yes | |
| payments.deposit_method | How deposits are paid today | yes | yes | |
| staff.roles | Who handles bookings, who guides, who approves refunds | yes | | |
| notifications.channels | How guests and staff are told (email, chat, SMS) | yes | | |
| storage.provider | Google or Microsoft account for files and the bookings sheet | yes | | storage.* |
| storage.admin | Who can create and share folders | yes | | |
