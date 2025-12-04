<?php

// Set content type to JSON for all responses
header('Content-Type: application/json');

// Helper function to round numeric values to 2 decimal places
function roundToTwoDecimals($value)
{
    if ($value === "" || $value === null || $value === false) {
        return "";
    }
    if (is_numeric($value)) {
        return round((float)$value, 2);
    }
    return $value;
}

// Function to prepare single weather data for API
function prepareWeatherData($weatherData)
{
    return [
        'idws' => isset($weatherData['idws']) ? $weatherData['idws'] : 99,
        'date' => isset($weatherData['date']) ? $weatherData['date'] : 0,
        'windspeedkmh' => isset($weatherData['windspeedkmh']) ? roundToTwoDecimals($weatherData['windspeedkmh']) : 0,
        'winddir' => isset($weatherData['winddir']) ? $weatherData['winddir'] : 0,
        'rain_rate' => isset($weatherData['rain_rate']) ? roundToTwoDecimals($weatherData['rain_rate']) : 0,
        'rain_today' => isset($weatherData['rain_today']) ? roundToTwoDecimals($weatherData['rain_today']) : 0,
        'temp_in' => isset($weatherData['temp_in']) ? roundToTwoDecimals($weatherData['temp_in']) : 0,
        'temp_out' => isset($weatherData['temp_out']) ? roundToTwoDecimals($weatherData['temp_out']) : 0,
        'hum_in' => isset($weatherData['hum_in']) ? $weatherData['hum_in'] : 0,
        'hum_out' => isset($weatherData['hum_out']) ? $weatherData['hum_out'] : 0,
        'uv' => isset($weatherData['uv']) ? roundToTwoDecimals($weatherData['uv']) : 0,
        'wind_gust' => isset($weatherData['wind_gust']) ? roundToTwoDecimals($weatherData['wind_gust']) : 0,
        'air_press_rel' => isset($weatherData['air_press_rel']) ? roundToTwoDecimals($weatherData['air_press_rel']) : 0,
        'air_press_abs' => isset($weatherData['air_press_abs']) ? roundToTwoDecimals($weatherData['air_press_abs']) : 0,
        'solar_radiation' => isset($weatherData['solar_radiation']) ? roundToTwoDecimals($weatherData['solar_radiation']) : 0,
        'dailyrainin' => isset($weatherData['dailyrainin']) ? roundToTwoDecimals($weatherData['dailyrainin']) : 0,
        'raintodayin' => isset($weatherData['raintodayin']) ? roundToTwoDecimals($weatherData['raintodayin']) : 0,
        'weeklyrainin' => isset($weatherData['weeklyrainin']) ? roundToTwoDecimals($weatherData['weeklyrainin']) : 0,
        'monthlyrainin' => isset($weatherData['monthlyrainin']) ? roundToTwoDecimals($weatherData['monthlyrainin']) : 0,
        'yearlyrainin' => isset($weatherData['yearlyrainin']) ? roundToTwoDecimals($weatherData['yearlyrainin']) : 0,
        'maxdailygust' => isset($weatherData['maxdailygust']) ? roundToTwoDecimals($weatherData['maxdailygust']) : 0,
        'wh65batt' => isset($weatherData['wh65batt']) ? roundToTwoDecimals($weatherData['wh65batt']) : 0
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
