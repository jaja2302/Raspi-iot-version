<?php

// Set content type to JSON for all responses
header('Content-Type: application/json');

// Function to prepare single weather data for API
function prepareWeatherData($weatherData)
{
    return [
        'idws' => isset($weatherData['idws']) ? $weatherData['idws'] : "",
        'date' => isset($weatherData['date']) ? $weatherData['date'] : "",
        'windspeedkmh' => isset($weatherData['windspeedkmh']) ? $weatherData['windspeedkmh'] : "",
        'winddir' => isset($weatherData['winddir']) ? $weatherData['winddir'] : "",
        'rain_rate' => isset($weatherData['rain_rate']) ? $weatherData['rain_rate'] : "",
        'rain_today' => isset($weatherData['rain_today']) ? $weatherData['rain_today'] : "",
        'temp_in' => isset($weatherData['temp_in']) ? $weatherData['temp_in'] : "",
        'temp_out' => isset($weatherData['temp_out']) ? $weatherData['temp_out'] : "",
        'hum_in' => isset($weatherData['hum_in']) ? $weatherData['hum_in'] : "",
        'hum_out' => isset($weatherData['hum_out']) ? $weatherData['hum_out'] : "",
        'uv' => isset($weatherData['uv']) ? $weatherData['uv'] : "",
        'wind_gust' => isset($weatherData['wind_gust']) ? $weatherData['wind_gust'] : "",
        'air_press_rel' => isset($weatherData['air_press_rel']) ? $weatherData['air_press_rel'] : "",
        'air_press_abs' => isset($weatherData['air_press_abs']) ? $weatherData['air_press_abs'] : "",
        'solar_radiation' => isset($weatherData['solar_radiation']) ? $weatherData['solar_radiation'] : "",
        'dailyrainin' => isset($weatherData['dailyrainin']) ? $weatherData['dailyrainin'] : "",
        'raintodayin' => isset($weatherData['raintodayin']) ? $weatherData['raintodayin'] : "",
        'weeklyrainin' => isset($weatherData['weeklyrainin']) ? $weatherData['weeklyrainin'] : "",
        'monthlyrainin' => isset($weatherData['monthlyrainin']) ? $weatherData['monthlyrainin'] : "",
        'yearlyrainin' => isset($weatherData['yearlyrainin']) ? $weatherData['yearlyrainin'] : "",
        'maxdailygust' => isset($weatherData['maxdailygust']) ? $weatherData['maxdailygust'] : "",
        'wh65batt' => isset($weatherData['wh65batt']) ? $weatherData['wh65batt'] : ""
    ];
}

// Only accept JSON raw data
$rawInput = file_get_contents('php://input');

// Check if input is empty
if (empty($rawInput)) {
    http_response_code(400);
    echo json_encode([
        'status' => 'error',
        'message' => 'No data received. Expected JSON format.'
    ], JSON_PRETTY_PRINT);
    exit;
}

// Parse JSON data
$jsonData = json_decode($rawInput, true);

// Check if JSON is valid
if (json_last_error() !== JSON_ERROR_NONE) {
    http_response_code(400);
    echo json_encode([
        'status' => 'error',
        'message' => 'Invalid JSON format: ' . json_last_error_msg()
    ], JSON_PRETTY_PRINT);
    exit;
}

// Check if data is array (required)
if (!is_array($jsonData)) {
    http_response_code(400);
    echo json_encode([
        'status' => 'error',
        'message' => 'Invalid data format. Expected JSON object or array of objects.'
    ], JSON_PRETTY_PRINT);
    exit;
}

// Check if it's bulk insert (array of objects) or single data (object)
$dataList = [];
if (isset($jsonData[0]) && is_array($jsonData[0])) {
    // Bulk insert: [{"idws": 10, ...}, {"idws": 10, ...}]
    $dataList = $jsonData;
} else {
    // Single data: {"idws": 10, ...}
    $dataList = [$jsonData];
}

// Process all data (support bulk insert)
$apiUrl = 'https://auth.srs-ssms.com/api/postDataAws';
$results = [];
$successCount = 0;
$failedCount = 0;

foreach ($dataList as $weatherData) {
    $postData = prepareWeatherData($weatherData);

    $ch = curl_init($apiUrl);
    curl_setopt($ch, CURLOPT_POST, 1);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlError = curl_errno($ch);

    if ($curlError) {
        $failedCount++;
        $results[] = [
            'status' => 'error',
            'message' => 'cURL Error: ' . curl_error($ch),
            'data' => $postData
        ];
    } else {
        $responseData = json_decode($response, true);

        if ($httpCode == 201) {
            $successCount++;
            $message = (is_array($responseData) && isset($responseData['message']))
                ? $responseData['message']
                : 'Success';
            $results[] = [
                'status' => 'success',
                'message' => $message,
                'data' => $postData
            ];
        } else {
            $failedCount++;
            $message = (is_array($responseData) && isset($responseData['message']))
                ? $responseData['message']
                : ($response ?: 'Unknown error');
            $results[] = [
                'status' => 'error',
                'message' => $message,
                'http_code' => $httpCode,
                'data' => $postData
            ];
        }
    }

    curl_close($ch);
}

// Return JSON response
$responseStatus = $failedCount == 0 ? 'success' : ($successCount > 0 ? 'partial' : 'error');
$httpResponseCode = $failedCount == 0 ? 200 : ($successCount > 0 ? 207 : 400); // 207 Multi-Status for partial

http_response_code($httpResponseCode);
echo json_encode([
    'status' => $responseStatus,
    'message' => $failedCount == 0
        ? 'All data processed successfully'
        : ($successCount > 0
            ? "Processed with errors: {$successCount} success, {$failedCount} failed"
            : 'All data processing failed'),
    'total' => count($dataList),
    'success_count' => $successCount,
    'failed_count' => $failedCount,
    'results' => $results
], JSON_PRETTY_PRINT);
