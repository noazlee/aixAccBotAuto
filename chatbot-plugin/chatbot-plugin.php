<?php
/*
Plugin Name: Chatbot Plugin
Description: A simple plugin to add a chatbot interface.
Version: 1.0
Author: Your Name
*/

// Enqueue scripts and styles
function chatbot_plugin_enqueue_scripts() {
    wp_enqueue_style('chatbot-plugin-style', plugins_url('style.css',__FILE__), array(),null);
    wp_enqueue_script('chatbot-plugin-script', plugin_dir_url(__FILE__) . '/script.js', array('jquery'), null, true);

    // Pass AJAX URL and API URL to script
    wp_localize_script('chatbot-plugin-script', 'chatbot_plugin_vars', array(
        'ajax_url' => admin_url('admin-ajax.php'),
        'api_url' => 'https://aixbot-l3ciz4wtia-de.a.run.app/chat'
    ));
}
add_action('wp_enqueue_scripts', 'chatbot_plugin_enqueue_scripts');

// Shortcode to display chatbot
function chatbot_plugin_shortcode() {
    $profile_picture_url = plugin_dir_url(__FILE__) . 'profile-picture.jpg';
    ob_start();
    ?>
    <div id="chatbot">
        <div id="chatbot-button" style="display: flex;">💬</div>
        <div id="chat-container" style="display: none;">
            <div id="profile-window">
                <img id="profile-picture" src="<?php echo $profile_picture_url; ?>" alt="Profile Picture">
                <span id="bot-name">AIX Bot</span>
            </div>
            <div id="chat-window">
                <div id="output"></div>
            </div>
            <div id="message-window">
                <input id="user-input" type="text" placeholder="Type your message here...">
                <button id="send-btn">Send</button>
            </div>
            <button id="close-btn" class="close-btn">✖</button>
        </div>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode('chatbot', 'chatbot_plugin_shortcode');

// Handle AJAX request
function chatbot_plugin_handle_request() {
    $message = sanitize_text_field($_POST['message']);

    $response = wp_remote_post('https://aixbot-l3ciz4wtia-de.a.run.app/chat', array(
        'body' => json_encode(array('message' => $message)),
        'headers' => array('Content-Type' => 'application/json')
    ));

    if (is_wp_error($response)) {
        wp_send_json_error(array('message' => 'Error connecting to the API.'));
    } else {
        $body = wp_remote_retrieve_body($response);
        wp_send_json_success(json_decode($body));
    }
}
add_action('wp_ajax_chatbot_plugin_handle_request', 'chatbot_plugin_handle_request');
add_action('wp_ajax_nopriv_chatbot_plugin_handle_request', 'chatbot_plugin_handle_request');
?>
