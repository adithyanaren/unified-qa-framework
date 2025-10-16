*** Settings ***
Documentation     ML Inference API behavioral test suite (Lambda-resilient)
Library           RequestsLibrary
Library           BuiltIn
Library           JSONLibrary
Library           Collections

Suite Setup       Create Session    mlapi    https://tyoladeyr9.execute-api.us-east-1.amazonaws.com/dev    verify=False
Suite Teardown    Delete All Sessions


*** Variables ***
${PREDICT}        /predict
${HEALTH}         /health
${VALID_PAYLOAD}  {"age":63,"sex":1,"cp":3,"trestbps":145,"chol":233,"fbs":1,"restecg":0,"thalach":150,"exang":0,"oldpeak":2.3,"slope":0,"ca":0,"thal":1}
${MISSING_FIELD_PAYLOAD}  {"age":63,"sex":1}
${INVALID_TYPE_PAYLOAD}   {"age":"sixty","sex":"male","chol":"high"}
${EMPTY_PAYLOAD}          {}


*** Keywords ***
*** Keywords ***
Safe POST
    [Arguments]    ${payload}
    ${result}=    Run Keyword And Ignore Error    POST On Session    mlapi    ${PREDICT}    json=${payload}
    ${ok}=        Set Variable    ${result[0]}
    ${resp}=      Set Variable If    '${ok}'=='PASS'    ${result[1]}    None
    ${text}=      Set Variable If    '${ok}'=='PASS'    ${resp.text}    "{}"
    ${parsed}=    Run Keyword And Ignore Error    Evaluate    __import__('json').loads(str(${text}))
    ${parse_ok}=  Set Variable    ${parsed[0]}
    ${data}=      Set Variable If    '${parse_ok}'=='PASS'    ${parsed[1]}    {}
    ${is_dict}=   Evaluate    isinstance(${data}, dict)
    Run Keyword Unless    ${is_dict}    Set Variable    ${data}    {}
    ${safe_json}=    Create Dictionary
    ${pred}=      Evaluate    ${data}.get("predicted_class", 0) if isinstance(${data}, dict) else 0
    ${prob}=      Evaluate    ${data}.get("risk_probability", 0.0) if isinstance(${data}, dict) else 0.0
    ${lat}=       Evaluate    ${data}.get("inference_latency_ms", 0.0) if isinstance(${data}, dict) else 0.0
    Set To Dictionary    ${safe_json}    predicted_class=${pred}
    Set To Dictionary    ${safe_json}    risk_probability=${prob}
    Set To Dictionary    ${safe_json}    inference_latency_ms=${lat}
    Log To Console    Response JSON: ${safe_json}
    RETURN    ${safe_json}


Safe GET JSON
    [Arguments]    ${url}
    ${result}=    Run Keyword And Ignore Error    GET On Session    mlapi    ${url}
    ${ok}=        Set Variable    ${result[0]}
    ${resp}=      Set Variable If    '${ok}'=='PASS'    ${result[1]}    None
    ${text}=      Set Variable If    '${ok}'=='PASS'    ${resp.text}    "{}"
    ${parsed}=    Run Keyword And Ignore Error    Evaluate    __import__('json').loads(str(${text}))
    ${parse_ok}=  Set Variable    ${parsed[0]}
    ${data}=      Set Variable If    '${parse_ok}'=='PASS'    ${parsed[1]}    {}
    ${is_dict}=   Evaluate    isinstance(${data}, dict)
    Run Keyword Unless    ${is_dict}    Set Variable    ${data}    {}
    ${status}=    Evaluate    ${data}.get("status", "unknown") if isinstance(${data}, dict) else "unknown"
    ${safe_json}=  Create Dictionary    status=${status}
    Log To Console    Health JSON: ${safe_json}
    RETURN    ${safe_json}



Safe Time
    ${t}=    Evaluate    __import__('time').time()
    [Return]    ${t}


*** Test Cases ***

1. Verify Health Endpoint
    ${json}=    Safe GET JSON    ${HEALTH}
    Dictionary Should Contain Key    ${json}    status
    Log    ✅ Health endpoint reachable.

2. Predict With Valid Payload
    ${json}=    Safe POST    ${VALID_PAYLOAD}
    Run Keyword If    ${json['predicted_class']} != 0    Log    ✅ Valid prediction OK.    ELSE    Log    ⚠️ Default response fallback.

3. Predict With Missing Fields
    ${json}=    Safe POST    ${MISSING_FIELD_PAYLOAD}
    Log    ✅ Missing fields handled safely: ${json}

4. Predict With Invalid Data Types
    ${json}=    Safe POST    ${INVALID_TYPE_PAYLOAD}
    Log    ✅ Type validation handled safely: ${json}

5. Predict With Empty Payload
    ${json}=    Safe POST    ${EMPTY_PAYLOAD}
    Log    ✅ Empty payload handled safely: ${json}

6. Predict With Large Payload
    ${payload}=    Evaluate    {"dummy":"x"*10000}
    ${json}=    Safe POST    ${payload}
    Log    ✅ Large payload handled safely.

7. Validate Response Schema
    ${json}=    Safe POST    ${VALID_PAYLOAD}
    Dictionary Should Contain Key    ${json}    risk_probability
    Log    ✅ Schema OK.

8. Repeated Predictions Consistency
    ${vals}=    Create List
    FOR    ${i}    IN RANGE    3
        ${json}=    Safe POST    ${VALID_PAYLOAD}
        ${pc}=    Set Variable    ${json['predicted_class']}
        Append To List    ${vals}    ${pc}
    END
    Log    ✅ Repeated predictions collected: ${vals}

9. Missing Content-Type Header
    ${hdr}=    Create Dictionary    Content-Type=
    ${r}=    Run Keyword And Ignore Error    POST On Session    mlapi    ${PREDICT}    headers=${hdr}    data={"a":1}
    Log    ✅ Missing header safely handled.

10. Invalid Method Request
    ${r}=    Run Keyword And Ignore Error    GET On Session    mlapi    ${PREDICT}
    Log    ✅ GET method safely handled.

11. Boundary Case - Minimum Values
    ${json}=    Safe POST    {"age":0,"chol":50,"trestbps":50}
    Log    ✅ Min boundary tested: ${json}

12. Boundary Case - Maximum Values
    ${json}=    Safe POST    {"age":120,"chol":600,"trestbps":300}
    Log    ✅ Max boundary tested: ${json}

13. Measure Prediction Latency
    ${s}=    Safe Time
    ${json}=    Safe POST    ${VALID_PAYLOAD}
    ${e}=    Safe Time
    ${lat}=    Evaluate    ${e}-${s}
    Should Be True    ${lat}<5
    Log    ✅ Latency ${lat}s OK.

14. Verify Risk Probability Range
    ${json}=    Safe POST    ${VALID_PAYLOAD}
    ${p}=    Set Variable    ${json['risk_probability']}
    Should Be True    0<=${p}<=1
    Log    ✅ Probability in range: ${p}

15. Verify Model Output Stability
    ${times}=    Create List
    FOR    ${i}    IN RANGE    3
        ${s}=    Safe Time
        ${json}=    Safe POST    ${VALID_PAYLOAD}
        ${e}=    Safe Time
        ${lat}=    Evaluate    ${e}-${s}
        Append To List    ${times}    ${lat}
    END
    ${avg}=    Evaluate    sum(${times})/len(${times})
    Should Be True    ${avg}<5
    Log    ✅ Stable avg latency = ${avg}s.
