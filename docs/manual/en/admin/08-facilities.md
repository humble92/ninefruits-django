# 8. Buildings and rooms

Menu: **Reference data > Buildings**, **Rooms** (`Manage buildings and rooms` permission)

## Buildings

Enter the code (for example `SCI`), the name (per language) and the address. A building that has rooms cannot be deleted, so turn off **Active** when it is no longer used.

## Rooms

| Field | Description |
|---|---|
| Building, Room number | Room numbers are unique within a building, for example `101` |
| Name | Optional, for example Main Auditorium |
| Room type | A value from the `room_type` code list (classroom, laboratory, etc.) |
| Org unit | The department that manages the room (optional) |
| Capacity | Compared with the section capacity when timetables are made (Phase 4) |
| Used for timetables | When off, the room is left out when timetables are made (offices, storage, etc.) |

For many rooms, use [CSV import](09-csv-import.md). Buildings must be registered first.
