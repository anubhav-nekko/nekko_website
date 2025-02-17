<?php
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $name = htmlspecialchars($_POST['name']);
    $email = filter_var($_POST['email'], FILTER_SANITIZE_EMAIL);
    $services = isset($_POST['services']) ? $_POST['services'] : [];
    
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        die("Invalid email format");
    }
    
    $to = "prithvi@nekko.tech";
    $subject = "New Work Request";
    
    $message = "Name: $name\n";
    $message .= "Email: $email\n";
    $message .= "Requested Services: " . implode(", ", $services) . "\n";
    
    $headers = "From: $email\r\n" .
               "Reply-To: $email\r\n" .
               "Content-Type: text/plain; charset=UTF-8\r\n";
    
    if (mail($to, $subject, $message, $headers)) {
        echo "Your request has been sent successfully.";
    } else {
        echo "Failed to send request. Please try again later.";
    }
} else {
    echo "Invalid request method.";
}
?>
