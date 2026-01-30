Bro, the system is broken at two key points, and we need to fix both.:

1. Critical bug: The purchase history does not load (error when clicking).
This may be due to:

A broken SQL query to the database (syntax error, incorrect table/column name).

Incorrect processing of data from the database (for example, the code expects a list, but None or an empty tuple arrives).

Error in forming a message for the user (an attempt to access a non-existent item in the list).

2. Critical bug: Payment is not credited, payment is "not found".
The problem is in the logic of checking the status from Yumani. Check the following points:

label or client_id: When creating a payment in Yuman, you pass a unique label (for example, user_123_tariff_5). Yumani returns the same label in the notification of a successful payment. The code should be searched in the database of pending payments for this label. If the label is generated or compared incorrectly, the payment will not be found.

Callback from Yumani: Make sure that the URL for notifications (HTTP callback) is correctly specified in the settings of the Yumani sales register and that your server accepts and processes it correctly (see yoomoney.log).

Status in the database: After a successful payment, the status in the database should be updated (for example, to 'succeeded'), and requests should be added to the user's balance. This logic may not exist or it crashes with an error.

What do you need to do?:

Check the logs (bot.log, yoomoney.log). When you click on "Purchase History", the Traceback (error call stack) will appear in the logs. He will point to the line of code where everything crashes. Fix this mistake first.

Give me examples of the identifiers used in the code. So that I can verify compliance, please send me code snippets or explain how your system generates:

the Yumani payment label (how is it created when generating a payment link?).

The structure of the table in the database where pending payments are stored (which columns?).

The code of the function that processes the callback from Yumani (or periodically checks the statuses).

The code of the function that loads the purchase history.

As soon as the purchase history starts working, we will immediately see the status of my "lost" payment (pending, succeeded, or not at all). This will narrow down the search for the second error.

P.S. Debugging idea: Temporarily add the /debug_payment {label} command for the admin, which will manually check the label payment status in the database and through the Yumani API and show all the logic steps. This will help you find the problem quickly.


Operation-details method
It allows you to get detailed information about an operation from its history.
Required token rights: operation-details.
Request
Parameters
Parameter	Type	Description
operation_id	string	The operation ID. The parameter value should be specified as the parameter value operation_id of the operation-history method response or the field value payment_id of the process-payment method response if the payer's account history is requested.
Request Example
POST /api/operation-details HTTP/1.1
Host: yoomoney.ru
Authorization: Bearer 410012345678901.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123
Content-Type: application/x-www-form-urlencoded
Content-Length: 20

operation_id=1234567
Answer
The method returns the following parameters:
Parameter	Type	Description
error	string	Error code is present when a request execution error occurs.
operation_id	string	Operation ID. The parameter value corresponds to either the parameter value operation_id of the operation-history method response, or, if the payer's account history is requested, the value of the payment_id field in the process-payment method response.
status	string	Payment (transfer) status. The parameter value corresponds to the value of the status field in the operation-history response.
pattern_id	string	The payment template ID that the payment was made with. Only present for payments.
direction
string
Direction of movement of funds. Can take the following values:
in (parish);
out (expense).
amount	amount	The amount of the transaction (the amount deducted from the account).
amount_due	amount	Amount to be received. Present for outgoing transfers to other users.
fee	amount	The amount of the commission. Present for outgoing transfers to other users.
datetime	datetime	Date and time of the transaction.
title	string	A brief description of the operation (store name or source of replenishment).
sender	string	The account number of the transfer sender. Present for incoming transfers from other users.
recipient	string	The recipient's transfer ID. Present for outgoing transfers to other users.
recipient_type
string
Type of the transfer recipient's identifier. Possible values:
account — the recipient's account number in the ЮMoney service;
phone — the recipient's linked mobile phone number;
email — email address of the transfer recipient.
Present for outgoing transfers to other users.
message	string	Message to the recipient of the transfer. Present for transfers to other users.
comment	string	Comment on a transfer or top-up. Present in the history of the transfer sender or the top-up recipient.
label	string	Payment label. Present for incoming and outgoing transfers to other YMoney users who have specified the label call parameter request-payment.
details	string	Detailed description of the payment. A string of arbitrary format that can contain any characters and line breaks. An optional parameter.
type	string	Operation type. For a description of possible operation types, see the description of the operation-history
digital_goods	object	Digital product data (game pins and bonuses, iTunes, Xbox, etc.) The field is present when a successful payment is made to digital product stores. Format description
Example of a response when making a payment to a merchant
JSON
{
  "operation_id": "1234567",
  "status": "success",
  "pattern_id": "2904",
  "amount": 500.00,
  "direction": "out",
  "datetime": "2011-07-11T20:43:00.000+04:00",
  "title": "Оплата ADSL-доступа компании Мой-Провайдер",
  "details": "Предоплата услуг ADSL-доступа в интернет компании ООО \"XXX\"\nНомер лицевого счета абонента: \n1234567/89\nЗачисленная сумма: 500.00\nНомер транзакции: 2000002967767",
  "type": "payment-shop"
}
Example response for an outgoing transfer to another user
JSON
{
  "operation_id": "1234567",
  "status": "success",
  "pattern_id": "p2p",
  "direction": "out",
  "amount": 50.25,
  "datetime": "2011-07-11T20:43:00.000+04:00",
  "title": "Перевод на счет 4100123456789",
  "recipient": "4100123456789",
  "recipient_type": "account",
  "message": "Купите бублики",
  "comment": "Перевод от пользователя ЮMoney",
  "codepro": false,
  "details": "Счет получателя:\n4100123456789\nСумма к получению: 50,00 руб.",
  "type": "payment-shop"
}
Error codes
If an operation fails, its code is returned:
Code	Description
illegal_param_operation_id	Invalid parameter value operation_id
All other values	Technical error, please try again later.
Example response when requesting a non-existent operation
JSON
{
 "error": "illegal_param_operation_id"
}

The account-info method
Getting information about the user's account status.
Required token Rights: account-info
Request
There are no input parameters.
Request Example
POST /api/account-info HTTP/1.1
Host: yoomoney.ru
Authorization: Bearer 410012345678901.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123
Content-Type: application/x-www-form-urlencoded
Content-Length: 0
Answer
If successful, it returns a JSON document with the following content:
Parameter	Type	Description
account	string	The user's account number.
balance	amount	The user's account balance.
currency	string	User account currency code. Always 643 (Russian ruble according to ISO 4217).
account_status
string
User's status. Possible values:
anonymous - anonymous account;
named — personal account;
identified — identified account.
account_type
string
User account type. Possible values:
personal — user's account in YUMOPEU;
professional — a professional account in YooMoney.
balance_details
object
Advanced balance information.
By default, this block is not present. The block appears if there are currently or have ever been enrollees in the queue, debts, blocking of funds.
see Object parameters balance_details
cards_linked
array
Information about linked bank cards.
If no cards are linked to the account, the parameter is missing. If at least one card is linked to the account, the parameter contains a list of data about the linked cards.
see cards_linked object parameters
Parameters of the balance_details object
Parameter	Type	Description
total	amount	Total account balance.
available	amount	The amount available for spending operations.
deposition_pending	amount	The amount of pending deposits. If there are no deposits in the queue, the parameter is missing.
blocked	amount	The amount of blocked funds by the decision of the executive authorities. If there are no blocked funds, the parameter is missing.
debt	amount	The amount of debt (negative account balance). If there is no debt, the parameter is missing.
hold	amount	The amount of frozen funds. If there are no frozen funds, the parameter is missing.
Parameters of the cards_linked object
Parameter	Type	Description
pan_fragment	string	Masked card number.
type
string
Map type. May be missing if unknown. Possible values:
VISA;
MasterCard;
AmericanExpress;
JCB.
Sample response
JSON
{
  "account": "4100123456789",
  "balance": 1000.00,
  "currency": "643",
  "account_status": "anonymous",
  "account_type": "personal",
  "cards_linked": [
    {
      "pan_fragment": "510000******9999",
      "type": "MasterCard"
    }
  ]
}


Request-payment method
Creating a payment, checking the parameters and the possibility of accepting a payment by the store or transferring funds to the user's YMoney account.
Required token Rights:
for payment to the store: payment.to-pattern ("payment template") or payment-shop.
to transfer funds to other users' accounts: payment.to-account ("recipient ID", "ID type") or payment-p2p.
Request
Payment to the merchant
The payment parameters for the store are specified by the counterparty when connecting through YuKassa. Additional information about the payment parameters is described in the payment acceptance protocol for stores.
Parameter	Type	Description
pattern_id	string	Payment template ID. Corresponds to the store's showcase number.scid
*	string	Payment template parameters required by the store.
Transfer of funds to other users ' accounts
Request Parameters:
Parameter	Type	Description
pattern_id	string	Fixed value: p2p.
to	string	The recipient's identifier (account number, phone number, or email address).
amount	amount	Amount to be paid (the amount the sender will pay).
amount_due	amount	Amount to be received (will be credited to the recipient's account after payment).
comment	string	The translation comment is displayed in the sender's history.
message	string	The translation comment is displayed to the recipient.
label	string	Payment label. Optional parameter.
Example of a request when transferring funds to another user's account
POST /api/request-payment HTTP/1.1
Host: yoomoney.ru
Authorization: Bearer 410012345678901.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123
Content-Type: application/x-www-form-urlencoded
Content-Length: 234

pattern_id=p2p&to=41001101140&amount=1000.00&message=%D0%9D%D0%B0%D0%B7%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5%20%D0%BF%D0%BB%D0%B0%D1%82%D0%B5%D0%B6%D0%B0&comment=%D0%A1%D0%BE%D0%BE%D0%B1%D1%89%D0%B5%D0%BD%D0%B8%D0%B5%20%D0%BF%D0%BE%D0%BB%D1%83%D1%87%D0%B0%D1%82%D0%B5%D0%BB%D1%8E
Example of a request when transferring funds to another user's account using the linked phone number
POST /api/request-payment HTTP/1.1
Host: yoomoney.ru
Authorization: Bearer 410012345678901.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123
Content-Type: application/x-www-form-urlencoded
Content-Length: 256

pattern_id=p2p&to=79219990099&identifier_type=phone&amount=1000.00&message=%d0%97%d0%b0+%d0%b2%d0%ba%d1%83%d1%81%d0%bd%d1%8b%d0%b9+%d0%b1%d1%83%d0%b1%d0%bb%d0%b8%d0%ba&comment=%d0%ba%d1%83%d0%bf%d0%b8%d1%82%d0%b5+%d0%b1%d1%83%d0%b1%d0%bb%d0%b8%d0%ba%d0%b8!
Transfer fee
The transfer amount is credited to the recipient minus the transfer fee. The transfer sender can specify only one of the following parameters:
amount — the amount that the sender will pay (including the service fee);
amount_due — the amount to be received, which will be credited to the recipient's account.
After sending request-payment, you can show the user the payment fee. The response will contain contract_amount, which can be used in the formula to calculate the fee:
Commission = contract_amount - amount_due
The commission is rounded mathematically to the nearest kopeck (2 decimal places). A commission less than a kopeck is always rounded up to 1 kopeck.
Payment Label
Any transfer can be assigned a payment label — label. A payment label is an identifier assigned by the application.
Subsequently, you can select transfers from the history by the specified label. For example, you can specify a code or an identifier of some entity in the application as a payment label. It is acceptable to use values up to 64 characters long. The label value is case-sensitive.
Answer
The method returns the following parameters:
Parameter	Type	Description
status
string
Operation result code. Possible values:
success — successful execution;
refused — payment failure, the reason for the failure is contained in the error. field. This is the final state of the payment.
error	string	Error code when making a payment (explanation for the status field). Only appears when there are errors.
money_source	object	Payment methods available for the application, see Available payment methods. Present only when the method is successfully executed.
request_id	string	Payment request ID. Present only when the method is successfully executed.
contract_amount	amount	The amount to be debited from the account in the currency of the payer's account (the amount the user will pay, including the commission). Present when the method is successfully executed or when an error occurs not_enough_funds.
balance
amount
The current balance of the user's account. Present when the following conditions are met:
method executed successfully;
the authorization token has the right account-info.
recipient_account_status
string
User's status. Possible values:
anonymous - anonymous account;
named — personal account;
identified — identified account
recipient_account_type	string	Recipient's account type. The parameter is present when the method is successfully executed in case of transferring funds to another user's YMoney account.
account_unblock_uri	string	The address to which the user should be sent to unlock the account. The field is present in case of error account_blocked.
ext_action_uri	string	The address to which the user should be sent to perform the necessary actions in case of an error ext_action_required.
When making a request, YooMoney usually communicates with the store's server, so the response time for the method can be up to 30 seconds. During the method's operation, request-payment the application should display a message to the user indicating that the application is waiting for a response from the store.
Successful execution of the request-payment method is not a guarantee of a successful payment process, as payment authorization is performed when the process-payment method is called.

Available payment methods
The response field money_source contains a list of available methods for making this payment. Each method contains a set of attributes.
If none of the following methods is possible for this payment, the money_source field will be empty.
Possible payment methods:
wallet — payment from the user's account;
cards — payment using bank cards linked to the account.
Attributes of the payment method from the user's account:
Attribute	Type	Description
allowed	boolean	This indicates that the payment method is allowed by the user.
Attributes of the payment method using a bank card:
Attribute	Type	Description
allowed	boolean	This indicates that the payment method is allowed by the user.
csc_required	boolean	A sign that you need to require a CVV2/CVC2 code to authorize a bank card payment.
item	object	Description of a bank card linked to an account.
Bank Card Description Parameters:
Attribute	Type	Description
id	string	The identifier of the bank card linked to the account. It must be specified in the process-payment method to make a payment using the selected card.
pan_fragment	string	A fragment of a bank card number. The field is only present for a linked bank card. It may be missing if it is unknown.
type
string
Map type. May be missing if unknown. Possible values:
Visa;
MasterCard;
American Express;
JCB.
If the payment method is available for this store and is allowed by the user, the response will include both the method name and the user's permission. For example:
"wallet": {
 "allowed": true
},
"cards": {
 "allowed": true,
 "csc_required": true,
 "items": [
 {
 "id": "card-385244400",
 "pan_fragment": "5280****7918",
 "type": "MasterCard"
 },
 {
 "id": "card-385244401",
 "pan_fragment": "4008****7919",
 "type": "Visa"
 }
 ]
}
If the method is available but not allowed by the user, the response will include the method name and a flag indicating that the user does not have permission. For example:
"wallet": {
 "allowed": false
},
"cards": {
 "allowed": false
}
The application may request additional rights to make payments. Requesting additional rights is done as a re-authorization of the application by the user.

Data about the transfer recipient
When requesting a transfer to another user's account, the request-payment method returns the following fields:
Code	Description
recipient_account_status
User's status. Possible values:
anonymous - anonymous account;
named — personal account;
identified — identified account.
recipient_account_type
Recipient account type. Possible values:
personal — user's account in YUMOPEU;
professional — a professional account in YooMoney.
Example of a successful response
JSON
{
  "status": "success",
  "wallet": {
  "allowed": true
  },
  "cards": {
    "allowed": true,
    "csc_required": true,
    "items": [
      {
        "id": "card-385244400",
        "pan_fragment": "5280****7918",
        "type": "MasterCard"
      },
      {
        "id": "card-385244401",
        "pan_fragment": "4008****7919",
        "type": "Visa"
      }
    ]
  },
  "request_id": "1234567",
  "contract": "Оплата услуг ОАО Суперфон Поволжъе, номер +7-9xx-xxx-xx-xx, сумма 300.00 руб.",
  "balance": 1000.00
}
Unwrap
Error codes
If an operation fails, its code is returned:
Code	Description
illegal_params	The required payment parameters are missing or have invalid values.
illegal_param_label	Invalid parameter value label.
illegal_param_to	Invalid parameter value to.
illegal_param_amount	Invalid parameter value amount.
illegal_param_amount_due	Invalid parameter value amount_due.
illegal_param_comment	Invalid parameter value comment.
illegal_param_message	Invalid parameter value message.
not_enough_funds	The payer's account does not have enough funds. You need to top up the account and make a new payment.
payment_refused	The store refused to accept the payment (for example, the user tried to pay for an item that is not available in the store).
payee_not_found	The recipient of the transfer could not be found. The specified account does not exist or a phone/email number not associated with the user's or the payment recipient's account is specified.
authorization_reject
Payment authorization has been denied. Possible reasons:
the transaction with the current parameters is prohibited for this user;
The user has not accepted the YooMoney Service Agreement.
limit_exceeded
One of the operation limits has been exceeded:
for the amount of the operation for the issued authorization token;
the amount of the transaction for the period of time for the issued authorization token;
restrictions on using UMoney for various types of transactions.
account_blocked	The user's account is locked. To unlock the account, please send the user to the address specified in the account_unblock_uri field.
account_closed	The user's account is closed.
ext_action_required
Currently, this type of payment cannot be processed. To be able to process such payments, the user must go to the page at ext_action_uri and follow the instructions on that page. These instructions may include the following steps:
enter your identification data,
accept the offer,
perform other actions according to the instructions.
all other values	Technical error, please retry the operation later.
Example of an opt-out response
JSON
{
  "status": "refused",
  "error": "payment_refused",
  "error_description": "Абонент не существует"
}

Process-payment method
Confirmation of a payment previously created using the request-payment. method.
Request
Parameter	Type	Description
request_id	string	The request ID obtained from the response of the request-payment method.
money_source
string
Requested payment method:
wallet — from the user's account
the ID of the card linked to the account (the value of the id bank card description field)
By default: wallet
csc	string	Card Security Code, CVV2/CVC2 code of the user's linked bank card. This parameter should only be specified when making a payment using a linked bank card.
ext_auth_success_uri	string	The return page address when a payment is successfully authenticated using a 3‑D Secure bank card. This is required if the application supports 3‑D Secure authentication.
ext_auth_fail_uri	string	The return page address when a payment is rejected by 3‑D Secure. Indicated if the application supports 3‑D Secure authentication. A mandatory parameter for such authentication.
Request example, payment from the user's account
POST /api/process-payment HTTP/1.1
Host: yoomoney.ru
Authorization: Bearer 410012345678901.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123
Content-Type: application/x-www-form-urlencoded
Content-Length: 18

request_id=1234567
Example request, payment from the user's linked bank card
POST /api/process-payment HTTP/1.1
Host: yoomoney.ru
Authorization: Bearer 410012345678901.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123
Content-Type: application/x-www-form-urlencoded
Content-Length: 44

request_id=1234567&money_source=card&csc=123
Answer
The method returns the following parameters:
Parameter	Type	Description
status
string
Operation result code. Possible values:
success — successful execution (payment is completed). This is the final state of the payment.
refused — payment failure. The reason for the failure is returned in the error. field. This is the final state of the payment.
in_progress — The payment authorization is not complete. The application should repeat the request with the same parameters after some time.
ext_auth_required — 3‑D Secure authentication is required to complete payment authorization using a bank card.
all other values - the payment status is unknown. The application should repeat the request with the same parameters after some time.
error	string	Error code when making a payment (explanation for the status field). Only appears when there are errors.
payment_id	string	The identifier of the completed payment. This parameter is only present when the method is successfully executed. This parameter corresponds to the operation_id parameter in the operation-history and operation-details methods of the payer's history.
balance
amount
The user's account balance after the payment is made. It is only available if the following conditions are met:
method executed successfully;
the authorization token has the right account-info.
invoice_id	string	The transaction number of the store in YooMoney. Present when the payment to the store is successful.
payer	string	The account number of the payer. Present when funds are successfully transferred to another user's YMoney account.
payee	string	The recipient's account number. This is present when funds are successfully transferred to another YMoney user's account.
credit_amount	amount	The amount received by the recipient. Present when funds are successfully transferred to another user's YMoney account.
account_unblock_uri	string	The address to which the user should be sent to unlock the account. The field is present in case of error account_blocked.
acs_uri	string	The address of the 3‑D Secure authentication page for the bank card on the issuing bank's side. The field is present if 3‑D Secure authentication is required to complete a transaction using a bank card.
acs_params	object	3‑D Secure card authentication parameters in the name-value collection format. The field is present if 3‑D Secure authentication is required to complete a transaction using a bank card.
next_retry	long	The recommended time to wait before repeating the request, in milliseconds. The field is present when status=in_progress.
digital_goods	object	Data about a digital product (game pins and bonuses, iTunes, Xbox etc). The field is present when a successful payment to digital product stores.
Other service fields may be included in the response, which do not need to be processed.

Sample response for successful payment authorization
JSON
{
  "status": "success",
  "payment_id": "2ABCDE123456789",
  "balance": 1000.00
}
Error codes
If an operation fails, its code is returned:
Code	Description
contract_not_found	There is no created (but not confirmed) payment with the specified request_id.
not_enough_funds	There are not enough funds in the payer's account. It is necessary to replenish the account and make a new payment.
limit_exceeded
One of the operation limits has been exceeded:
for the amount of the operation for the issued authorization token;
the amount of the transaction for the period of time for the issued authorization token;
restrictions on using UMoney for various types of transactions.
money_source_not_available	The requested payment method (money_source) is not available for this payment.
illegal_param_csc	The parameter csc is missing or has an invalid value.
payment_refused
Payment has been denied. Possible reasons:
the store refused to accept the payment (request checkOrder);
A transfer to a YooMoney user is not possible (for example, if the recipient's wallet balance limit has been exceeded).
authorization_reject
Payment authorization has been denied. Possible reasons:
your bank card has expired;
the issuing bank rejected the card transaction;
exceeded the limit for this user;
the transaction with the current parameters is prohibited for this user;
The user has not accepted the YooMoney Service Agreement.
account_blocked	The user's account is locked. To unlock the account, please send the user to the address specified in the account_unblock_uri field.
illegal_param_ext_auth_success_uri	The parameter ext_auth_success_uri is missing or has an invalid value.
illegal_param_ext_auth_fail_uri	The parameter ext_auth_fail_uri is missing or has an invalid value.
all other values	The payment authorization has been denied. The application should make a new payment after some time.
Example of an opt-out response
JSON
{
  "status": "refused",
  "error": "not_enough_funds"
}
Payment with a linked bank card
Necessary conditions for making a payment using a linked bank card:
a bank card is linked to the user's YooMoney account;
the user has allowed the app to use a bank card for payments;
payment is made to the merchant;
The store can accept payments using bank cards.
The payment time from a linked bank card (money_source=card) is determined by the transaction processing time of the card issuing bank. In addition, YooMoney can contact the store's server, and the response time also affects the payment authorization time.
If payment authorization takes more than 1 minute, the method process-paymentreturns the operation result code in_progress. The application should repeat the method call process-paymentwith the same parameters every 1 minute until the final response is received (status it must have the value successorrefused).
Example response in case of incomplete payment authorization
JSON
{
  "status": "in_progress"
}
If the application does not receive a response, it is not possible to determine the status of the payment. The payment may be either successful or unsuccessful. To resolve the payment status, you should repeat the call process-payment with the same parameters.

If the payment is made using a bank card, additional verification of the customer using 3-D Secure technology may be required.
3‑D Secure authentication payment scenario
Step 1. The request-payment method is called with the payment parameters.
Step 2. The method process-payment is called with the following parameters: money-source=card, csc, code, ext_auth_success_uri, ext_auth_fail_uri.
Example of a request when paying with a bank card using an app that supports 3‑D Secure
POST /api/process-payment HTTP/1.1
Host: yoomoney.ru
Authorization: Bearer 410012345678901.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123
Content-Type: application/x-www-form-urlencoded
Content-Length: 164

request_id=1234567&money-source=card&csc=123&ext_auth_success_uri=http%3A%2F%2Fclient.example.com%2Fsuccess&ext_auth_fail_uri=http%3A%2F%2Fclient.example.com%2Ffail
Step 3. The process-payment method returns status=ext_auth_required, acs_uri, acs_params.
Example response when 3‑D Secure authentication is required
JSON
{
  "status": "ext_auth_required",
  "acs_uri": "https://acs.alfabank.ru/acs/PAReq",
  "acs_params": {
    "MD": "723613-7431F11492F4F2D0",
    "PaReq": "eJxVUl1T2zAQ/CsZv8f6tCR7LmLSGiidJjAldMpTR7XVxAN2gmynSX59JeNAebu9O93u7QkuDvXzZG9dW22bWURiHE1sU2zLqlnPoofV1VRFFxpWG2dtfm+L3lkNC9u2Zm0nVTmLVvn9r7v5d/uS/UkYt4b8tjibUiGVxazICMeSSkmtwBmlhYw="
  }
}
Step 4. The application should open a browser and make a POST request to acs_uri with parameters acs_params as application/x-www-form-urlencoded (similar to HTML form submit).
Step 5. The client is authenticated according to the issuing bank's scenario and is redirected via HTTP 302 Redirect to one of the addresses, depending on the result: ext_auth_success_uri or ext_auth_fail_uri.
Step 6. The application should re-invoke the process-payment method, specifying only one parameter, request_id.
Example of a repeated request when paying with a bank card using an app after 3‑D Secure authentication
POST /api/process-payment HTTP/1.1
Host: yoomoney.ru
Authorization: Bearer 410012345678901.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123
Content-Type: application/x-www-form-urlencoded
Content-Length: 18

request_id=1234567
Step 7. The process-payment method returns status=success or refused.
Data about digital products
When a payment is successful in a digital goods store, the response contains a digital_goods field that contains a list of goods and a list of bonuses.
Data about a digital product or bonus:
Parameter	Type	Description
merchantArticleId	string	Product ID in the seller's system. Only available for products.
serial	string	Product serial number (the open part of the pin code, activation code, or login).
secret	string	The secret of a digital product (the hidden part of a pin code, activation code, password, or download link).
Example of digital products
JSON
"digital_goods": {
  "article": [
    {
      "merchantArticleId": "1234567",
      "serial": "EAV-0087182017",
      "secret": "87actmdbsv"
    },
    {
      "merchantArticleId": "1234567",
      "serial": "2000012",
      "secret": "gjhkgjsuurtrghxchfhjkrwetuertrehtthh"
    },
    {
      "merchantArticleId": "1234567",
      "serial": "2000013",
      "secret": "77788sfs7fd89g89dfg77778dfgdjkert789"
    }
  ],
  "bonus": [
    {
      "serial": "XXXX-XX-XX",
      "secret": "0000-1111-2222-3333-4444"
    }
  ]
}

Request for a description of a pre-filled form
The request is intended to redisplay the payment form to the customer with pre-filled field values, allowing for convenient repetition of previously completed operations.
Request
The form description with pre-filled field values is requested using the POST method at the same address where the payment form description is requested:
Method Address
https://yoomoney.ru/api/showcase/<pattern_id>
Content-Type: application/x-www-form-urlencoded, character encoding is UTF‑8.
The request must contain a list of form field values in the format field name-value.
The response of this method cannot be cached, as its contents depend on the request arguments.

Heading	Description
Accept-Language
The language code in which the client wants to receive the form description, according to RFC-5646: Tags for Identifying Languages, IANA Language Subtag Registry.
Possible values:
ru — Russian;
en - English.
By default: ru
Accept-Encoding
Indication of client support for traffic compression. Supported values: gzip — support for GZIP transfer encoding (RFC-1952: GZIP file format specification).
By default, traffic compression is not applied.
Request Example
POST /api/showcase/5506 HTTP/1.1
Host: yoomoney.ru
Content-Type: application/x-www-form-urlencoded
Content-Length: 28
Accept-Language: ru
Accept-Encoding: gzip

skypename=username&netSum=10

Sending a form or form step to the server
Request
The address for submitting the form is contained in the Location header of the response to the form description request or the response to submitting the form data from the previous step of a multi-step form.
The client should always take the form submission address from the server response and never remember it for later use.

Data should be sent using the POST method, with Content-Type: application/x-www-form-urlencoded and UTF‑8 encoding.
The request must contain the following parameters::
the contents of all visible UI-controls of the form;
the contents of the hidden_fields block, if it is present in the form description.
If the form's UI control is visible, optional, and the customer has not entered anything in it, the control's field name and an empty value are added to the request. Web browsers behave in the same way.

The request may contain the following HTTP headers:
Heading	Description
Accept-Language
The language code in which the client wants to receive the form description, according to RFC-5646: Tags for Identifying Languages, IANA Language Subtag Registry.
Possible values:
ru — Russian;
en - English.
By default: ru
Accept-Encoding
Indication of client support for traffic compression. Supported values: gzip — support for GZIP transfer encoding (RFC-1952: GZIP file format specification).
By default, traffic compression is not applied.
Request Example
POST /api/showcase/validate/5551/step_INN_3038 HTTP/1.1
Host: yoomoney.ru
Content-Type: application/x-www-form-urlencoded
Content-Length: 115
Accept-Language: ru
Accept-Encoding: gzip

supplierInn=4704020508&ShopID=13423&ShopArticleID=35241&ShowCaseID=3005&ContractTemplateID=524867&budgetDocNumber=0
Answer
The method returns one of the following response options:
a sign of successful form data validation and payment options is the final state of the form;
a success indicator for form data validation and a description of the next form step;
a list of errors in the data entered by the customer and a description of the current form step.
The response of this method cannot be cached, as its content depends on the data entered by the customer.

Possible HTTP response codes:
HTTP response code	Description
200 OK	The data entered by the customer has been successfully verified; this is the last step of the form. The response contains a list of parameters for making a payment.
300 Multiple Choices	The data entered by the customer has been successfully verified; the next step of the form is present. The response contains a description of the next step of the payment form. The address for sending the next step of the form is specified in the HTTP header Location.
400 Bad Request	The client has entered incorrect data in the form fields. The response contains a list of form validation errors and a description of the current form step with values pre-filled by the customer. The address for resending the form is specified in the HTTP header Location. The client should correct the form data and resend it.
404 Not Found	The requested payment method does not exist or is not allowed. No response body.
500 Internal Server Error	The service is temporarily unavailable for technical reasons.
List of payment parameters
The list of parameters for making a payment is a collection of name-value pairs. This set should be passed as parameters for calling the payment functions from the YooMoney wallet.
Response format with a list of payment parameters
JSON
{
  "params": {
    "param1": "value1",
    "param2": "value2",
    ...
    "paramN": "valueN"
  }
}
Example: The customer's entered data has been successfully verified, and the payment parameters have been returned
JSON
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 197
Cache-Control: no-cache

{"params":{"pattern_id":"5506","ContractTemplateID":"525923","sc_param_scid":"5506","netSum":"2","ShopArticleID":"71747","sc_param_step":"","ShopID":"14061","ShowCaseID":"6101","skypename":"test"}}
Verification of data entered by the buyer
The server checks all the values of the form fields and their logical combinations.
If errors are found, the server returns the following response:
description of the current step of the form with pre-filled field values entered by the customer;
list of errors in the block error.
Each element of the error list contains:
Field	Description
name	The name of the field that contains an invalid value. If the error cannot be attributed to a specific form field, this parameter is missing.
alert	Text of the error message.
Response format with a list of errors in the data entered by the customer
JSON
{
  ... описание текущего шага формы ...
  "form": [
    ...
  ],
 "error": [
    {
      "name": "field1",
      "alert": "Сообщение об ошибке"
    },
    ...
    {
      "name": "fieldN",
      "alert": "Сообщение об ошибке"
    }
    ...
    {
      "alert": "Сообщение об ошибке, которое не может отнесено к конкретному полю формы"
    }
  ]
}
Unwrap
Example: The data entered by the customer contains errors, and a document containing the error reason is returned
JSON
HTTP/1.1 400 Bad Request
Location: https://yoomoney.ru/api/showcase/validate/5506/
Content-Type: application/json
Content-Length: 733
Cache-Control: no-cache                                                           

{"title":"Skype","form":[{"type":"group","layout":"VBox","items":[{"type":"text","name":"FormComment","value":"Skype","label":"Название","required":false,"readonly":false},{"type":"text","name":"skypename","label":"Логин в Skype","required":true,"readonly":false},{"type":"amount","name":"netSum","value":"2","label":"Сумма","required":true,"readonly":false,"min":0.01,"max":375,"currency":"EUR"}]},{"type":"submit","label":"Заплатить"}],"money_source":["wallet","cards","payment-card","cash"],"hidden_fields":{"ContractTemplateID":"525923","sc_param_scid":"5506","netSum":"2","ShopArticleID":"71747","sc_param_step":"","ShopID":"14061","ShowCaseID":"6101"},"error":[{"name":"skypename","alert":"Пожалуйста, укажите логин в Skype"}]}
Request
Answer
List of payment parameters
Verification of data entered by 


Request for a form description
The form description is requested using the GET method at the following address:
https://yoomoney.ru/api/showcase/<pattern_id>
The request is equivalent to downloading a document from a remote server.
It is recommended to cache simple form descriptions on the client side, as form descriptions are rarely changed.
Subsequent steps of multi-step forms cannot be cached, as their state depends on the data entered by the customer in the first step.
Request
Request format
GET /api/showcase/<pattern_id> HTTP/1.1
Host: yoomoney.ru
Accept-Language: <lang>
Accept-Encoding: <gzip>
If-Modified-Since: <date>
Request URL Parameters:
Attribute	Type	Description
pattern_id	string	ID of the payment template.
The request may contain the following HTTP headers:
Heading	Description
Accept-Language
The language code in which the client wants to receive the form description, according to RFC-5646: Tags for Identifying Languages, IANA Language Subtag Registry.
Possible values:
ru — Russian;
en - English.
By default: ru
Accept-Encoding
Indication of client support for traffic compression. Supported values: gzip — support for GZIP transfer encoding (RFC-1952: GZIP file format specification).
By default, traffic compression is not applied.
If-Modified-Since
If the payment form description was saved in the client's cache, the Last-Modified value of the server's response to the previous request is indicated.
If the client does not cache form descriptions, the header is not specified.
Answer
The method returns one of the following response options:
description of the payment form;
indicating that the form does not exist;
indicating that a different form should be used;
an indication that the form has not changed since the previous request.
Possible HTTP response codes:
HTTP response code	Description
300 Multiple Choices	Success, the response contains a description of the payment form. The address for submitting the form is specified in the HTTP header Location
301 Moved Permanently	Instead of the requested payment form, you should use another form. The address of the new form is specified in the HTTP header Location. There is no response body.
304 Not Modified	The description of the payment form has not changed since the previous request. There is no response body.
404 File Not Found	The requested payment method does not exist or is not allowed. No response body.
500 Internal Server Error	The service is temporarily unavailable for technical reasons.
The server response contains the following special HTTP headers:
HTTP response code	Description
Location	Address to send the form data to the server. Or a new form address if you want to use a different form.
Content-Encoding	gzip, if the client has requested traffic compression.
Cache-Control
Indicates the client-side caching mode. Possible values:
private — the payment form description should be cached on the client side;
no-cache — the payment form description is not allowed to be cached.
Last-Modified	Date and time of the last change to the form description.
For clarity, some of the examples below are uncompressed and formatted. The server returns a compressed JSON-compact format.
Example: a simple form or the first step of a multi-step form is returned
HTTP/1.1 300 Multiple Choices
Location: https://yoomoney.ru/api/showcase/5551
Content-Type: application/json
Content-Length: 539
Cache-Control: private
Last-Modified: Thu, 17 Jul 2014 09:00:25 GMT

{
 "money_source":
 [
 "wallet",
 "cards",
 "payment-card",
 "cash"
 ],
 "title":"Receipts",
 "hidden_fields":{
 "ShopID":"13423",
 "ShopArticleID":"35241",
 "ShowCaseID":"3005",
 "ContractTemplateID":"524867",
 "budgetDocNumber":"0",
 "has_external_status":"",
 "is_withdrawal":""
 },
 "form":
 [
 {
 "type":"text",
 "name":"supplierInn",
 "hint":"10 digits (for IP - 12 digits)",
 "label":"Recipient's INN:",
 "alert":"Please specify the recipient's TIN",
 "required":true,
 "readonly":false,
 "minlength":10,
 "maxlength":12,
 "pattern":"^\\d{10}$|^\\d{12}$"
 },
 {
 "type":"submit",
 "label":"Continue"
 }
 ]
}
Unwrap
Example: Redirection to a new form
HTTP/1.1 301 Moved Permanently
Location: https://yoomoney.ru/api/showcase/5551
Example: the payment form does not exist or is not allowed to be used
HTTP/1.1 404 Not Found
Content-Length: 0