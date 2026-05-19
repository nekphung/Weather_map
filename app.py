from flask import Flask, render_template_string, jsonify, request
import requests
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import os


app = Flask(__name__)

# ─────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────
OWM_BASE_GEO = "https://api.openweathermap.org/geo/1.0/direct"
OWM_BASE_WEATHER = "https://api.openweathermap.org/data/2.5/weather"
OWM_BASE_FORECAST = "https://api.openweathermap.org/data/2.5/forecast"

load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not API_KEY:
    raise ValueError("Thiếu OPENWEATHER_API_KEY")

REQUEST_TIMEOUT = 10


# ─────────────────────────────────────────────────────────
# WEATHER FUNCTIONS
# ─────────────────────────────────────────────────────────
def get_city_lat_lon(city_name: str):
    params = {
        "q": city_name,
        "limit": 1,
        "appid": API_KEY,
    }

    response = requests.get(
        OWM_BASE_GEO,
        params=params,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    data = response.json()

    if not data:
        raise Exception("Không tìm thấy thành phố")

    return data[0]["lat"], data[0]["lon"]


def fetch_current_weather(lat, lon):
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
        "units": "metric",
    }

    response = requests.get(
        OWM_BASE_WEATHER,
        params=params,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()
    return response.json()


def fetch_forecast(lat, lon):
    params = {
        "lat": lat,
        "lon": lon,
        "cnt": 32,
        "appid": API_KEY,
        "units": "metric",
    }

    response = requests.get(
        OWM_BASE_FORECAST,
        params=params,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()
    return response.json()


# ─────────────────────────────────────────────────────────
# API
# ─────────────────────────────────────────────────────────
@app.route("/api/weather/city")
def api_weather_city():

    city = request.args.get("city", "").strip()

    if not city:
        return jsonify({
            "error": "Thiếu tham số city"
        }), 400

    try:
        lat, lon = get_city_lat_lon(city)

        with ThreadPoolExecutor(max_workers=2) as executor:

            current_future = executor.submit(
                fetch_current_weather,
                lat,
                lon
            )

            forecast_future = executor.submit(
                fetch_forecast,
                lat,
                lon
            )

            current = current_future.result()
            forecast = forecast_future.result()

        return jsonify({
            "current": current,
            "forecast": forecast,
            "lat": lat,
            "lon": lon
        })

    except requests.exceptions.HTTPError:
        return jsonify({
            "error": "Lỗi API thời tiết"
        }), 500

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "Request timeout"
        }), 500

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/api/weather/coords")
def api_weather_coords():

    lat = request.args.get("lat")
    lon = request.args.get("lon")

    if not lat or not lon:
        return jsonify({
            "error": "Thiếu lat/lon"
        }), 400

    try:

        lat = float(lat)
        lon = float(lon)

        with ThreadPoolExecutor(max_workers=2) as executor:

            current_future = executor.submit(
                fetch_current_weather,
                lat,
                lon
            )

            forecast_future = executor.submit(
                fetch_forecast,
                lat,
                lon
            )

            current = current_future.result()
            forecast = forecast_future.result()

        return jsonify({
            "current": current,
            "forecast": forecast,
            "lat": lat,
            "lon": lon
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500
    
# ─────────────────────────────────────────────────────────
# HTML
# ─────────────────────────────────────────────────────────
HTML = r"""
<!DOCTYPE html>
<html lang="vi">

<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>WeatherMap</title>

<link rel="stylesheet"
href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"/>

<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>

<style>

*{
    margin:0;
    padding:0;
    box-sizing:border-box;
}

body{
    background:#0b1220;
    color:white;
    font-family:Arial;
    height:100vh;
    display:flex;
    flex-direction:column;
}

header{
    height:70px;
    background:#121b2e;
    display:flex;
    align-items:center;
    gap:10px;
    padding:0 20px;
    border-bottom:1px solid #1f2d45;
}

header h1{
    color:#4af0c4;
    font-size:22px;
}

.search-box{
    display:flex;
    gap:10px;
    flex:1;
    max-width:500px;
}

.search-box input{
    flex:1;
    padding:12px;
    border:none;
    border-radius:10px;
    background:#1a2438;
    color:white;
}

.search-box button{
    padding:12px 18px;
    border:none;
    border-radius:10px;
    background:#4af0c4;
    font-weight:bold;
    cursor:pointer;
}

.main{
    flex:1;
    display:flex;
    overflow:hidden;
}

#map{
    flex:1;
}

.sidebar{
    width:360px;
    background:#111827;
    overflow-y:auto;
    border-left:1px solid #1f2d45;
}

.card{
    background:#1a2438;
    margin:14px;
    border-radius:14px;
    padding:16px;
}

.temp{
    font-size:72px;
    font-weight:bold;
    color:#4af0c4;
}

.desc{
    font-size:18px;
    margin-top:6px;
}

.meta{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:10px;
    margin-top:16px;
}

.meta-item{
    background:#0f172a;
    padding:12px;
    border-radius:10px;
}

.meta-label{
    font-size:12px;
    color:#94a3b8;
}

.meta-value{
    font-size:20px;
    margin-top:4px;
}

.hourly{
    display:flex;
    overflow-x:auto;
    gap:10px;
}

.hour{
    min-width:70px;
    background:#0f172a;
    border-radius:10px;
    padding:10px;
    text-align:center;
}

.day{
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:12px;
    background:#0f172a;
    border-radius:10px;
    margin-top:10px;
}

.loading{
    display:flex;
    justify-content:center;
    align-items:center;
    height:100%;
    font-size:20px;
}

.error{
    margin:20px;
    background:#7f1d1d;
    padding:14px;
    border-radius:10px;
}
@media (max-width: 768px){

    .main{
        flex-direction:column;
    }

    #map{
        width:100%;
        height:45vh;
    }

    .sidebar{
        width:100%;
        height:55vh;
    }

    header{
        flex-direction:column;
        height:auto;
    }
}

</style>
</head>

<body>

<header>

<h1>WeatherMap</h1>

<div class="search-box">

<input
    type="text"
    id="searchInput"
    placeholder="Nhập tên thành phố..."
    onkeydown="if(event.key==='Enter') searchWeather()"
/>

<button onclick="searchWeather()">
    Tìm
</button>

<button onclick="getCurrentLocation()">
    📍 Vị trí hiện tại
</button>

</div>

</header>

<div class="main">

<div id="map"></div>

<div class="sidebar" id="sidebar">

<div class="loading">
🌍 Chọn thành phố để xem thời tiết
</div>

</div>

</div>

<script>

const map = L.map('map').setView([14.0583,108.2772],6);

L.tileLayer(
'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
{
    attribution: '© OpenStreetMap © CARTO',
    maxZoom: 19
}
).addTo(map);

let marker = null;

function weatherIcon(desc){

    desc = desc.toLowerCase();

    if(desc.includes('rain')) return '🌧️';
    if(desc.includes('cloud')) return '☁️';
    if(desc.includes('clear')) return '☀️';
    if(desc.includes('storm')) return '⛈️';

    return '🌤️';
}

function setLoading(){

    document.getElementById('sidebar').innerHTML = `
        <div class="loading">
            ⏳ Đang tải...
        </div>
    `;
}

function setError(msg){

    document.getElementById('sidebar').innerHTML = `
        <div class="error">
            ⚠️ ${msg}
        </div>
    `;
}

function formatCoord(value, pos, neg){

    return `${Math.abs(value).toFixed(4)}° ${value >= 0 ? pos : neg}`;
}

function renderWeather(data){

    const current = data.current;
    const forecast = data.forecast;

    const temp = Math.round(current.main.temp);

    const desc = current.weather[0].description;

    const icon = weatherIcon(desc);

    const hourly = forecast.list.slice(0,8).map(item => {

        const date = new Date(item.dt * 1000);

        return `
            <div class="hour">
                <div>${String(date.getHours()).padStart(2,'0')}:00</div>
                <div style="font-size:22px;margin:6px 0">
                    ${weatherIcon(item.weather[0].description)}
                </div>
                <div>${Math.round(item.main.temp)}°</div>
            </div>
        `;
    }).join('');
    const byDay = {};

    forecast.list.forEach(item => {

        const d = new Date(item.dt * 1000);

        const key = `${d.getFullYear()}-${
            d.getMonth()
        }-${d.getDate()}`;

        if(!byDay[key]){
            byDay[key] = [];
        }

        byDay[key].push(item);
    });

    const today = new Date();

    const todayKey = `${today.getFullYear()}-${
        today.getMonth()
    }-${today.getDate()}`;

    const dailyHTML = Object.entries(byDay)
    .filter(([k]) => k !== todayKey)
    .slice(0,3)
    .map(([, slots]) => {

        const d = new Date(slots[0].dt * 1000);

        const temps = slots.map(s => s.main.temp);

        const maxT = Math.round(Math.max(...temps));
        const minT = Math.round(Math.min(...temps));

        const mid = slots[Math.floor(slots.length / 2)];

        return `
            <div class="day">

                <div>
                    <div style="font-weight:bold">
                        ${
                            d.toLocaleDateString(
                                'vi-VN',
                                { weekday:'long' }
                            )
                        }
                    </div>

                    <div style="font-size:12px;color:#94a3b8">
                        ${d.getDate()}/${d.getMonth()+1}
                    </div>
                </div>

                <div style="font-size:26px">
                    ${weatherIcon(mid.weather[0].description)}
                </div>

                <div>
                    ${mid.weather[0].description}
                </div>

                <div style="text-align:right">
                    <div>${maxT}°</div>
                    <div style="color:#94a3b8">${minT}°</div>
                </div>

            </div>
        `;
    }).join('');

    document.getElementById('sidebar').innerHTML = `

        <div class="card">

            <h2>${current.name}</h2>

            <div style="margin-top:6px;color:#94a3b8">
                ${formatCoord(data.lat,'N','S')}
                ·
                ${formatCoord(data.lon,'E','W')}
            </div>

        </div>

        <div class="card">

            <div class="temp">${temp}°</div>

            <div class="desc">
                ${icon} ${desc}
            </div>

            <div class="meta">

                <div class="meta-item">
                    <div class="meta-label">Độ ẩm</div>
                    <div class="meta-value">
                        ${current.main.humidity}%
                    </div>
                </div>

                <div class="meta-item">
                    <div class="meta-label">Gió</div>
                    <div class="meta-value">
                        ${current.wind.speed} m/s
                    </div>
                </div>

                <div class="meta-item">
                    <div class="meta-label">Cảm giác</div>
                    <div class="meta-value">
                        ${Math.round(current.main.feels_like)}°
                    </div>
                </div>

                <div class="meta-item">
                    <div class="meta-label">Áp suất</div>
                    <div class="meta-value">
                        ${current.main.pressure}
                    </div>
                </div>

            </div>

        </div>

        <div class="card">

            <h3 style="margin-bottom:14px">
                24 giờ tới
            </h3>

            <div class="hourly">
                ${hourly}
            </div>

        </div>
        <div class="card">

        <h3 style="margin-bottom:14px">
            3 ngày tiếp theo
        </h3>

        ${dailyHTML}

    </div>
    `;
}

async function searchWeather(){

    const city = document
        .getElementById('searchInput')
        .value
        .trim();

    if(!city) return;

    setLoading();

    try{

        const response = await fetch(
            `/api/weather/city?city=${encodeURIComponent(city)}`
        );

        const data = await response.json();

        if(data.error){
            setError(data.error);
            return;
        }

        map.flyTo([data.lat, data.lon], 10);

        if(marker){
            map.removeLayer(marker);
        }

        marker = L.marker([data.lat, data.lon]).addTo(map);

        marker.bindPopup(`
            <b>${data.current.name}</b><br>
            ${Math.round(data.current.main.temp)}°C
        `).openPopup();

        renderWeather(data);

    }catch(err){

        setError('Không thể tải dữ liệu thời tiết');

    }
}

async function getCurrentLocation(){

    if(!navigator.geolocation){

        setError('Trình duyệt không hỗ trợ định vị');

        return;
    }

    setLoading();

    navigator.geolocation.getCurrentPosition(

        async(position) => {

            try{

                const lat = position.coords.latitude;
                const lon = position.coords.longitude;

                map.flyTo([lat, lon], 11);

                if(marker){
                    map.removeLayer(marker);
                }

                marker = L.marker([lat, lon]).addTo(map);

                const response = await fetch(
                    `/api/weather/coords?lat=${lat}&lon=${lon}`
                );

                const data = await response.json();

                if(data.error){

                    setError(data.error);
                    return;
                }

                renderWeather(
                    {
                        ...data,
                        current:{
                            ...data.current,
                            name:"📍 Địa điểm hiện tại"
                        }
                    }
                );

                marker.bindPopup(`
                    <b>📍 Địa điểm hiện tại</b><br>
                    ${Math.round(data.current.main.temp)}°C
                `).openPopup();

            }catch(err){

                setError('Không lấy được thời tiết');

            }

        },

        (err) => {

            setError('Bạn chưa cho phép truy cập vị trí');

        }
    );
}

</script>

</body>
</html>
"""


# ─────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template_string(HTML)


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)