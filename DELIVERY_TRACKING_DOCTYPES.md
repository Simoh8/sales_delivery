# Delivery Tracking DocTypes

This document describes the DocTypes created for the delivery tracking system in the ledgerctrl app.

## Overview

Four new DocTypes have been created to support comprehensive delivery tracking with GPS logs, assignment history, and event logging:

1. **Delivery Job** - Main delivery record
2. **Assignment History** - Track driver assignments
3. **GPS Log** - Store GPS location data
4. **Delivery Event** - Log delivery events and status changes

## 1. Delivery Job

**Path**: `ledgerctrl/ledgerctrl/doctype/delivery_job/`

**Purpose**: Main record for tracking a delivery job from creation to completion.

### Key Fields

**Basic Information**:
- `customer` - Link to Customer doctype
- `customer_name` - Auto-fetched customer name
- `customer_address` - Delivery address
- `customer_contact` - Contact information
- `delivery_note` - Link to ERPNext Delivery Note
- `delivery_trip` - Link to ERPNext Delivery Trip
- `driver` - Assigned driver (Employee)
- `driver_name` - Auto-fetched driver name
- `vehicle` - Assigned vehicle
- `scheduled_date` - Scheduled delivery date
- `scheduled_time` - Scheduled delivery time

**Status**:
- `status` - Current status (Pending, Dispatched, Accepted, En Route, Arrived, In Progress, Completed, Cancelled, Failed)
- `priority` - Priority level (Low, Normal, High, Urgent)
- `estimated_distance` - Estimated distance in km
- `estimated_duration` - Estimated duration in minutes

**Location**:
- `latitude` - Destination latitude
- `longitude` - Destination longitude
- `location_accuracy` - GPS accuracy in meters

**Timing**:
- `dispatched_at` - Timestamp when dispatched
- `accepted_at` - Timestamp when driver accepted
- `en_route_at` - Timestamp when driver started route
- `arrived_at` - Timestamp when driver arrived at location
- `started_delivery_at` - Timestamp when delivery started
- `completed_at` - Timestamp when delivery completed
- `cancelled_at` - Timestamp if cancelled

**Actual Performance**:
- `actual_distance` - Actual distance traveled
- `actual_duration` - Actual duration in minutes
- `delay_minutes` - Delay in minutes (calculated)

**Items**:
- `items` - Child table with delivery items (Delivery Job Item)

**Payment**:
- `grand_total` - Total amount
- `payment_status` - Payment status (Unpaid, Paid, Partial)

**Notes**:
- `delivery_notes` - Delivery notes
- `special_instructions` - Special delivery instructions

**Metadata**:
- `created_via` - How it was created (Manual, API, Mobile App)
- `created_by` - User who created it
- `modified_by` - User who last modified
- `modified_at` - Last modification timestamp

### Child Table: Delivery Job Item

**Fields**:
- `item_code` - Item link
- `item_name` - Item name (auto-fetched)
- `qty` - Quantity
- `uom` - Unit of measure
- `rate` - Rate
- `amount` - Total amount (calculated)

### Methods

- `update_status(new_status, notes)` - Update status with validation
- `add_gps_log(latitude, longitude, accuracy, speed)` - Add GPS log entry
- `assign_driver(driver_id, vehicle_id)` - Assign driver and log history

### Status Flow

```
Pending → Dispatched → Accepted → En Route → Arrived → In Progress → Completed
         ↓
      Cancelled
         ↓
         Failed → Pending
```

## 2. Assignment History

**Path**: `ledgerctrl/ledgerctrl/doctype/assignment_history/`

**Purpose**: Track all driver assignments and reassignments for delivery jobs.

### Key Fields

**Basic Information**:
- `delivery_job` - Link to Delivery Job
- `driver` - Assigned driver
- `driver_name` - Auto-fetched driver name
- `vehicle` - Assigned vehicle
- `assigned_by` - User who made the assignment
- `assigned_at` - Assignment timestamp
- `assigned_via` - Assignment method (Manual, Auto-Assignment, API, Mobile App)

**Status**:
- `assignment_status` - Status (Assigned, Accepted, Rejected, Unassigned, Completed)
- `accepted_at` - When driver accepted
- `rejected_at` - When driver rejected
- `unassigned_at` - When unassigned (reassignment)

**Details**:
- `notes` - Notes about assignment
- `reason_for_change` - Reason for status change

**Location**:
- `driver_location_at_assignment` - Driver's location when assigned
- `distance_to_job` - Distance to job in km
- `estimated_arrival_time` - Estimated arrival time in minutes

### Methods

- `mark_accepted()` - Mark assignment as accepted
- `mark_rejected(reason)` - Mark assignment as rejected
- `mark_unassigned(reason)` - Mark assignment as unassigned

### Status Flow

```
Assigned → Accepted → Completed
   ↓
  Rejected → Unassigned
   ↓
  Unassigned
```

## 3. GPS Log

**Path**: `ledgerctrl/ledgerctrl/doctype/gps_log/`

**Purpose**: Store GPS location data for tracking driver movements.

### Key Fields

**Basic Information**:
- `delivery_job` - Link to Delivery Job (optional)
- `driver` - Driver
- `driver_name` - Auto-fetched driver name
- `vehicle` - Vehicle
- `timestamp` - GPS timestamp
- `created_via` - How it was created (Mobile App, API, Manual)

**Location Data**:
- `latitude` - Latitude (required)
- `longitude` - Longitude (required)
- `location_accuracy` - Accuracy in meters
- `altitude` - Altitude in meters
- `altitude_accuracy` - Altitude accuracy
- `heading` - Heading in degrees
- `speed` - Speed in km/h

**Metadata**:
- `battery_level` - Device battery level
- `location_provider` - GPS provider (GPS, Network, Passive, Fused)
- `satellite_count` - Number of satellites
- `address` - Reverse geocoded address
- `notes` - Additional notes

### Validation

- Latitude must be between -90 and 90
- Longitude must be between -180 and 180

### Static Methods

- `get_latest_location(driver, delivery_job)` - Get latest GPS location
- `get_location_history(delivery_job, start_time, end_time)` - Get GPS history
- `cleanup_old_logs(days_to_keep)` - Delete logs older than specified days

### Scheduled Cleanup

GPS logs are automatically cleaned up after 30 days (configurable) via scheduled task.

## 4. Delivery Event

**Path**: `ledgerctrl/ledgerctrl/doctype/delivery_event/`

**Purpose**: Log all events related to a delivery job for audit trail and analysis.

### Key Fields

**Basic Information**:
- `delivery_job` - Link to Delivery Job
- `event_type` - Type of event (Status Change, Assignment, Reassignment, Arrival, Departure, Delivery Attempt, Delivery Success, Delivery Failed, Delay, Exception, Custom)
- `timestamp` - Event timestamp
- `created_by` - User who created the event

**Status Change**:
- `old_status` - Previous status
- `new_status` - New status

**Details**:
- `notes` - Event notes
- `reason` - Reason for event

**Location**:
- `latitude` - Event location latitude
- `longitude` - Event location longitude
- `location_accuracy` - Location accuracy

**Metadata**:
- `created_via` - How it was created (Mobile App, API, Manual, System)
- `customer_notified` - Whether customer was notified
- `notification_method` - Notification method (SMS, Email, Push, WhatsApp, Phone)
- `attachment` - Any attachment (photo, signature, etc.)

### Event Types

1. **Status Change** - Status transitions
2. **Assignment** - Driver assigned
3. **Reassignment** - Driver reassigned
4. **Arrival** - Driver arrived at location
5. **Departure** - Driver departed from location
6. **Delivery Attempt** - Attempted delivery
7. **Delivery Success** - Successful delivery
8. **Delivery Failed** - Failed delivery
9. **Delay** - Delivery delayed
10. **Exception** - Exception occurred
11. **Custom** - Custom event

### Static Methods

- `log_event(delivery_job, event_type, ...)` - Helper to log an event
- `get_event_timeline(delivery_job)` - Get all events for a job
- `get_recent_events(driver, limit)` - Get recent events by driver
- `get_events_by_type(delivery_job, event_type)` - Get events by type
- `cleanup_old_events(days_to_keep)` - Delete events older than specified days

### Scheduled Cleanup

Delivery events are automatically cleaned up after 90 days (configurable) via scheduled task.

## Relationships

```
Delivery Job
    ├── Delivery Job Item (child table)
    ├── Assignment History (linked)
    ├── GPS Log (linked)
    └── Delivery Event (linked)
```

## Permissions

### System Manager
- Full access (create, read, write, delete, share, email, export, print, report)

### Driver
- Delivery Job: create, read, write, share, email, export, print, report
- Assignment History: read, share, email, export, print, report
- GPS Log: create, read, write, share, email, export, print, report
- Delivery Event: create, read, write, share, email, export, print, report

### Sales Person
- Delivery Job: create, read, write, delete, share, email, export, print, report
- Assignment History: create, read, write, share, email, export, print, report
- GPS Log: read, share, email, export, print, report
- Delivery Event: read, share, email, export, print, report

## API Integration

These DocTypes are designed to work with the JWT authentication system and mobile app APIs:

1. **Delivery Job** - Created/updated via mobile app
2. **Assignment History** - Auto-created when driver is assigned
3. **GPS Log** - Created periodically by mobile app background location service
4. **Delivery Event** - Auto-created on status changes and manually for exceptions

## Next Steps

### 1. Run Migration

```bash
cd /home/simon/frappe-bench-v15
bench migrate
```

### 2. Create APIs

Create API endpoints in `ledgerctrl/api/` for:
- Creating/updating delivery jobs
- Submitting GPS logs
- Logging delivery events
- Fetching assignment history
- Getting delivery timelines

### 3. Integrate with Existing ERPNext

Connect with:
- **Delivery Note** - Create delivery jobs from delivery notes
- **Delivery Trip** - Link delivery jobs to delivery trips
- **Customer** - Fetch customer addresses
- **Employee** - Get driver information
- **Vehicle** - Track vehicle assignments

### 4. Create Dashboard

Create dashboards to visualize:
- Active deliveries
- Driver performance
- Delivery completion rates
- GPS tracking visualization
- Delay analysis

## Data Flow Example

```
1. Delivery Note created in ERPNext
   ↓
2. Delivery Job created (status: Pending)
   ↓
3. Driver assigned → Assignment History created
   ↓
4. Job dispatched → Status: Dispatched, GPS logging starts
   ↓
5. Driver accepts → Status: Accepted, Event logged
   ↓
6. GPS logs submitted every 30 seconds
   ↓
7. Driver en route → Status: En Route, Event logged
   ↓
8. Driver arrives → Status: Arrived, Event logged
   ↓
9. Delivery started → Status: In Progress, Event logged
   ↓
10. Delivery completed → Status: Completed, Event logged
    ↓
11. Actual duration and delay calculated
    ↓
12. Delivery Note updated in ERPNext
```

## Storage Management

To manage database growth, the following scheduled tasks have been configured:

- **GPS Logs**: Cleaned up after 30 days (daily)
- **Delivery Events**: Cleaned up after 90 days (weekly)
- **Refresh Tokens**: Cleaned up on expiry (daily)

Adjust retention periods in the respective DocType methods as needed.
