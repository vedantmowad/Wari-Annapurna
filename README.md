# 🍊 Wari Annapurna

### Crowd-Mobility Based Smart Food Rediscovery Platform for Pandharpur Wari

> **Wari Annapurna** is a smart food redistribution and crowd-aware food discovery platform designed to reduce food wastage and improve food accessibility during the **Pandharpur Wari**.

The platform connects **Varkaris, Annadan Centres, Food Donors, NGOs, Volunteers, and Administrators** through a unified system that uses crowd mobility and food availability data to intelligently match food supply with demand.

---

## 🌟 Problem Statement

During the Pandharpur Wari, thousands of Varkaris travel through different locations every day. Large quantities of food are prepared and distributed through **Annadan Centres**, but demand varies significantly from one location to another.

This creates two major problems:

* 🍱 **Food wastage** at centres with surplus food
* 🍽️ **Food shortages** at centres experiencing high demand
* 👥 Difficulty in knowing where food is currently available
* 📍 Lack of real-time information about nearby food centres
* 🚶 Difficulty coordinating food redistribution based on crowd movement
* 📶 Connectivity challenges in rural and high-crowd areas

---

## 💡 Our Solution

**Wari Annapurna** provides a centralized platform that combines:

* 📍 Live Annadan Centre discovery
* 👥 Crowd mobility monitoring
* 🍱 Food availability tracking
* 📊 Demand-supply analysis
* 🔄 Surplus food redistribution
* 🤝 Volunteer coordination
* ⭐ Centre rating and feedback
* 🌐 Public food discovery
* 🗣️ Multilingual and voice-assisted access

The system analyzes **crowd density, food availability, location, and movement patterns** to identify areas where food demand is higher than supply.

---

## 🎯 Key Objectives

1. Reduce food wastage during the Wari.
2. Improve accessibility to available food.
3. Match food supply with crowd demand.
4. Provide real-time information about Annadan Centres.
5. Support NGOs, donors and volunteers in redistribution.
6. Enable data-driven decision making for administrators.
7. Provide an accessible multilingual interface for Varkaris.

---

# 🏗️ System Architecture

```text
                    ┌──────────────────────────┐
                    │       USERS / ACTORS     │
                    │                          │
                    │ Varkari | Donor | NGO    │
                    │ Volunteer | Admin        │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │       FRONTEND            │
                    │                          │
                    │ HTML + CSS + JavaScript  │
                    │ Bootstrap + Leaflet Maps │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │       FLASK BACKEND       │
                    │                          │
                    │ Authentication            │
                    │ REST APIs                 │
                    │ Demand Analysis           │
                    │ Crowd Processing          │
                    │ Food Matching             │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │       MYSQL DATABASE      │
                    │                          │
                    │ Users                     │
                    │ Food Services             │
                    │ Annadan Centres           │
                    │ Crowd Locations           │
                    │ Ratings                   │
                    └──────────────────────────┘
```

---

# 🚀 Main Features

## 👤 Varkari Portal

The Varkari portal helps pilgrims quickly find available food.

### Features

* 📍 Find nearby Annadan Centres
* 🍛 View available meals
* 🕐 View meal timings
* 👥 View estimated crowd/demand
* 🗺️ Interactive map
* ⭐ Rate Annadan Centres
* 📝 Submit reviews
* 🌐 Marathi, Hindi and English support
* 🗣️ Voice assistance

---

## 🍱 Annadan Centre Management

Annadan Centres can manage their food services and availability.

### Features

* Register/manage centre information
* Add breakfast, lunch and dinner services
* Update available meals
* Define serving timings
* Track food availability
* Monitor demand and shortages

---

## 📦 Food Donor Portal

Donors can contribute surplus food and track redistribution.

### Features

* Register food donations
* Track available food
* View food distribution statistics
* Monitor meals served
* Support redistribution to areas with higher demand

---

## 🤝 NGO / Volunteer Coordination

NGOs and volunteers can help move surplus food to areas where it is needed.

The system can assist with:

```text
Food Surplus
     ↓
Identify High-Demand Area
     ↓
Match Supply & Demand
     ↓
Assign Volunteer / NGO
     ↓
Redistribute Food
```

---

## 👨‍💼 Admin Dashboard

The administrator can monitor the overall system.

### Dashboard Information

* Total Annadan Centres
* Food availability
* Crowd distribution
* Demand and supply
* Food redistribution
* User activity
* Centre ratings
* System statistics

---

# 🧠 Smart Demand-Supply Matching

One of the core components of Wari Annapurna is its **demand-supply analysis**.

The system considers factors such as:

* 👥 Crowd size
* 🍱 Available meals
* 📍 Distance
* 🕐 Meal timing
* 📊 Demand at nearby centres
* 🚶 Crowd movement

A simplified representation:

```text
              Crowd Data
                  │
                  ▼
        ┌───────────────────┐
        │ Demand Estimation │
        └─────────┬─────────┘
                  │
                  ▼
       Compare Demand & Supply
                  │
          ┌───────┴───────┐
          ▼               ▼
       Surplus          Shortage
          │               │
          ▼               ▼
     Redistribution    Food Support
```

---

# 👥 Crowd Mobility

Wari Annapurna uses crowd-location data to understand how people are moving around different food centres.

Each crowd record can contain:

```text
Varkari ID
Latitude
Longitude
Centre
Zone
Movement
Timestamp
```

Movement states include:

* `approaching`
* `leaving`
* `stationary`

This information can be used to understand:

> **Where people are moving and where food demand is likely to increase.**

---

# 📍 Location Intelligence

The platform uses geographical coordinates to calculate distances between Varkaris and Annadan Centres.

The system can identify nearby centres based on the user's location.

```text
Varkari Location
       │
       ▼
Calculate Distance
       │
       ▼
Nearby Centres
       │
       ├── Food Available
       ├── Crowd Level
       ├── Meal Timing
       └── Demand
```

The map interface is powered by **Leaflet**.

---

# ⭐ Centre Rating System

Varkaris can provide feedback about Annadan Centres.

Each review contains:

```text
Centre
Varkari
Rating (1–5)
Review
Timestamp
```

This creates a feedback mechanism that can help identify high-quality and reliable food centres.

---

# 🌐 Multilingual Support

The Varkari-facing interface supports:

* 🇮🇳 Marathi
* 🇮🇳 Hindi
* 🇬🇧 English

This makes the platform more accessible to users from different backgrounds.

---

# 🗣️ Voice Assistance

The public Varkari portal includes a voice-assistance feature to improve accessibility.

The interface can use browser-based speech capabilities to provide voice interaction and assistance.

This is particularly useful for users who may have difficulty navigating a traditional web interface.

---

# 📡 Offline / Low-Connectivity Approach

Pandharpur Wari routes can experience network congestion and limited connectivity.

The platform can be designed to support low-connectivity scenarios through:

* Cached essential information
* Lightweight web pages
* Reduced API payloads
* Local storage for temporary data
* Graceful handling of network failures
* Synchronization when connectivity returns

The objective is to ensure that essential information remains accessible even when internet connectivity is unstable.

---

# 🗄️ Database

The application uses **MySQL** for persistent data storage.

### Major entities

```text
Users
  │
  ├── Varkaris
  ├── Donors
  ├── NGOs
  ├── Volunteers
  └── Admins

Annadan Centres
  │
  └── Meal Services

Crowd Locations
  │
  └── Mobility Data

Ratings
  │
  └── Centre Feedback
```

---

# 🔌 REST APIs

The backend exposes REST APIs for communication between the frontend and server.

Example:

```http
GET /warkari/api/nearby-centres
```

Public API:

```http
GET /warkari/public/api/nearby-centres
```

Centre listing:

```http
GET /warkari/public/api/centres
```

These APIs allow the frontend to retrieve dynamic information without reloading the complete application.

---

# 🛠️ Technology Stack

| Layer           | Technology            |
| --------------- | --------------------- |
| Frontend        | HTML, CSS, JavaScript |
| UI Framework    | Bootstrap             |
| Templates       | Jinja2                |
| Maps            | Leaflet               |
| Backend         | Python + Flask        |
| API             | REST API              |
| Database        | MySQL                 |
| Server          | Gunicorn              |
| Deployment      | Render                |
| Version Control | Git + GitHub          |

---

# 📁 Project Structure

```text
wari-annapurna/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   │
│   ├── auth/
│   ├── admin/
│   ├── donor/
│   ├── ngo/
│   ├── volunteer/
│   ├── warkari/
│   └── public_warkari/
│
├── templates/
│   ├── admin/
│   ├── donor/
│   ├── ngo/
│   ├── volunteer/
│   └── warkari/
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── database/
│   └── schema.sql
│
├── requirements.txt
├── Procfile
├── runtime.txt
├── run.py
└── README.md
```

---

# ⚙️ Installation

## 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd wari-annapurna
```

## 2. Create a virtual environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure the database

Create a MySQL database and update the database configuration in:

```text
app/config.py
```

Example:

```python
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "your_password"
DB_NAME = "wari_annapurna"
```

Import the database schema:

```bash
mysql -u root -p wari_annapurna < database/schema.sql
```

---

## 5. Run the application

```bash
python run.py
```

The application will be available at:

```text
http://127.0.0.1:5000
```

---

# 🌍 Deployment

The application can be deployed using a cloud platform such as **Render**.

Example production command:

```bash
gunicorn run:app --bind 0.0.0.0:$PORT
```

Environment variables should be used for sensitive credentials such as:

```text
DB_HOST
DB_USER
DB_PASSWORD
DB_NAME
SECRET_KEY
```

---

# 🔐 Security Considerations

The production system should include:

* Password hashing
* Role-based access control
* Secure session management
* Environment variables for secrets
* Input validation
* SQL injection protection
* API authentication where required
* HTTPS
* Rate limiting for public APIs

---

# 💡 Innovation & Uniqueness

### 1. Crowd-Aware Food Redistribution

Instead of considering only food availability, the platform considers **where people are moving and where demand is increasing**.

### 2. Demand-Supply Intelligence

The platform identifies potential food shortages and surpluses rather than simply displaying food centres.

### 3. Mobility-Based Decision Making

Crowd movement data provides an additional layer of intelligence for food planning.

### 4. Public Food Discovery

Varkaris can discover food centres without requiring a complex registration process.

### 5. Multilingual Accessibility

Marathi, Hindi and English interfaces make the platform more practical for a large and diverse user base.

### 6. Integrated Ecosystem

The platform connects:

```text
Varkari
   ↕
Annadan Centre
   ↕
Donor
   ↕
NGO
   ↕
Volunteer
   ↕
Admin
```

---

# 📈 Expected Impact

Wari Annapurna aims to:

* ♻️ Reduce food wastage
* 🍛 Improve food accessibility
* 🚶 Improve crowd-aware food distribution
* 🤝 Improve coordination between organizations
* 📍 Help Varkaris find food quickly
* 📊 Enable data-driven Wari management
* 🌱 Promote sustainable food utilization

---

# 🔮 Future Scope

The platform can be extended with:

### 🤖 AI-Based Demand Prediction

Predict future food demand using:

* Historical crowd data
* Time of day
* Location
* Wari schedule
* Previous food consumption
* Crowd movement patterns

### 🛰️ Real-Time GPS Integration

Replace simulated crowd data with real-time location information.

### 📊 Advanced Analytics

Provide administrators with:

* Heatmaps
* Demand forecasts
* Food wastage analytics
* Centre performance
* Crowd-flow predictions

### 🔔 Smart Notifications

Notify Varkaris when:

* Food is available nearby
* A centre becomes crowded
* Another nearby centre has shorter queues

### 🚚 Automated Redistribution Planning

Optimize routes for volunteers transporting surplus food.

### 📱 Progressive Web App

Convert the platform into a PWA for improved offline capabilities and mobile accessibility.

---

# 👨‍💻 Development Team

**Wari Annapurna** was developed as a technology-driven solution for improving food distribution and accessibility during the Pandharpur Wari.

### Core Development Areas

* Backend Development
* Frontend Development
* Database Design
* REST API Development
* Crowd-Mobility Processing
* Demand-Supply Matching
* UI/UX
* Deployment

---

# 🤝 Contributing

Contributions are welcome.

```bash
git checkout -b feature/new-feature
git add .
git commit -m "Add new feature"
git push origin feature/new-feature
```

Then create a Pull Request.

---

# 📄 License

This project is developed for educational, innovation and hackathon purposes.

---

# ❤️ Built for Wari

**Wari Annapurna — Connecting Food, People and Need.**

> *Reducing food waste by making the right food reach the right people at the right place and time.*
