<?php

function get_from_url($url) {
    $ch = curl_init();

    curl_setopt(
        $ch,
        CURLOPT_URL,
        $url
    );
    curl_setopt($ch, CURLOPT_HTTPHEADER, array("Content-type: application/json"));
    
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

    $result = curl_exec($ch);
    if ($result === FALSE) {
        die(curl_error($ch));
    }

    curl_close($ch);
    
    return $result;
};

$api_key = "5bb5b735a977e851ad763edc771edc66c7515a3";
$address = urlencode($_GET["address"]);

echo get_from_url("https://api.geocod.io/v1.7/geocode?fields=cd,stateleg&q=" . $address . "&api_key=" . $api_key);

?>