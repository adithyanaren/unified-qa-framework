*** Settings ***
Library    RequestsLibrary
Library    Collections
Variables  ../../utils/config.py

*** Test Cases ***
Verify Lambda CRUD API Health
    Create Session    mysession    ${API_URL}
    ${response}=    GET On Session    mysession    /
    Should Be Equal As Integers    ${response.status_code}    200
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    message
    Should Be Equal    ${json["message"]}    Hello from Lambda CRUD API!
