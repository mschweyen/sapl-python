# SAPL Integration library for Flask

This library enables the usage of SAPL for a Flask application by providing decorators to enforce functions with SAPL functionality.
Basic knowledge about Attributes based access control(ABAC) is beneficial to understand the functionality of this library.

If you don't have any knowledge about ABAC, you should read the SAPL [documentation](https://sapl.io/documentation) before you continue reading.

## What is SAPL

SAPL is a further development of ABAC and can be described as Attribute-Stream-Based Access Control (ASBAC).
In contrary to ABAC, which is based on a request-response model and demands a new connection whenever a new decision is 
needed, SAPL works on a publish/subscribe model.
The client sends an Authorization Subscription to the Policy Decision Point(PDP) and receives a stream of Decisions, 
which can update the decision for the given Subscription for the client. 

The functionality of updating and enforcing newly received Decisions is done by the library in the background, so the 
developer can concentrate on writing the policies.

A complete documentation of SAPL can be found at [https://sapl.io](https://sapl.io), which also contains a playground to
write policies.


## how to install

The SAPL Flask integration library is released on PyPI and can be installed with the Package Manager pip.

To install SAPL_Flask you can use `pip install sapl_flask`. 

## Initialize the library

To initialize the library, the `init_sapl` function, which takes two arguments has to be called.

`def init_sapl(config: Config, subject_functions: list[[Callable[[dict], dict]]]):`

The first argument is an argument of the type Configuration, which works exactly like a dictionary.
The 2nd argument is a list of functions, which take a dictionary as argument and returns a dictionary.
What these functions are and how to write them is explained in the section [How to write subject functions](#how-to-write-subject-functions).

A simple project, which initializes SAPL_Flask and starts a Flask application would look like this:
<!--- Ich würde hier Beispiele zeigen, die auch irgendie einen Sinn ergeben, so dass man die Funktionalität besser versteht -->
```Python
import sapl_flask
from flask import Flask

app = Flask(__name__)
def subject_function(values:dict):
    return {"return_value": "subject"}

if __name__ == "__main__":
    sapl_flask.init_sapl(app.config, [subject_function])
    app.run()
```

## How to configure SAPL_Flask

The configuration is used to determine, how to connect to the PDP.
This PDP should be a SAPL server, for which a documented open source version is available on 
[GitHub](https://github.com/heutelbeck/sapl-policy-engine/tree/master/sapl-server-lt).

The easiest way to configure SAPL_Flask is to add a key `"POLICY_DECISION_POINT"` with according values to your Flask 
Configuration and use your Flask Configuration as the 1st argument of the init method.

The default configuration in JSON Format looks like this:
```json
{
  "POLICY_DECISION_POINT" : {
    "base_url": "http://localhost:8080/api/pdp/",
    "key": "YJidgyT2mfdkbmL",
    "secret": "Fa4zvYQdiwHZVXh",
    "dummy": false,
    "verify": false,
    "debug": false,
    "backoff_const_max_time": 1
  }
}
```
- base_url: The URL, where your PDP Server is located. This has to include the path `'/api/pdp/'` of the PDP Server. 
- key: Access to the API of the SAPL PDP Server requires "Basic Auth". The client key (username) can be set with this parameter.
  The default is the default implemented credentials of a [SAPL-Server-lt](https://github.com/heutelbeck/sapl-policy-engine/tree/master/sapl-server-lt)
- secret: The password which is used to get access to the API. Please note that the secret has to be BCrypt encoded. <!--- auf dieser Seite ist es doch nicht BCrypt encoded -->
- dummy: Enables a dummy PDP, which is used instead of a remote PDP. This PDP always grants access and should never be used in production. 
- verify: <!--- was passiert hier? -->
- debug: Enables debugging , which adds logging.
- backoff_const_max_time: When an error occurs, while requesting a Decision from the PDP SAPL_Flask does a retry. 
  This parameter determines, how long the library should retry to connect, before it aborts and denies the access. <!--- welche Einheit? Anzahl Versuche? Sekunden? -->

# Subject functions

For authentication, it has to be known who(subject) does the request. Flask does not have authentication built in 
from which the library could gather information about who did the request.
To determine who is requesting something you need to provide functions, which create the subject for an Authorization 
Subscription. These functions are called, whenever an Authorization Subscription is created. 
The dictionarys these functions return are merged to create the subject for the Authorization Subscription.

## How to write subject functions

Subject functions can be any functions which take a dictionary as argument and return a dictionary.
These functions are called, when an Authorization Subscription is created and are called with a dictionary as argument.
The given dictionary contains the function, which shall be enforced and the arguments with which this function is called.
The given dictionary JSON formatted would look like this:
```json
{
  "values" : {
    "function" : function,
    "args" : {"arg_1": "argument", "arg_2":  "another argument"}
  }
}
```

An example for a subject function, where the name of the enforced function is used to create the subject could be:
```Python
def subject_function(values:dict):
  return {"function_name" : values.get("function").__name__}
```
If multiple subject_functions are provided, the dictionarys are merged into one dictionary.

<!--- Auch hier finde ich die Beispiele wenig hilfreich. Wie oben beschrieben beschreib das subject das who. Ein function_name ist das wohl eher ein schlechtes Beispiel. Sinvoller ist vielleicht so etwas wie {'username: get_username_from_session()} --> 

<!--- Ist das mit der subject_function Liste wirklich sinnvoll. Einfacher fände ich es nur eine Funktion zuzulassen. Das kombinieren kann man dann ja selbst übernehmen und kann damit auf Kollisionen direkt vermeiden -->
A Flask project, which uses SAPL_Flask, which is initialized with default configuration and this subject_function would be:
```Python
import sapl_flask
from flask import Flask

app = Flask(__name__)
def subject_function(values:dict):
  return {"function_name" : values.get("function").__name__}

if __name__ == "__main__":
    sapl_flask.init_sapl(app.config, [subject_function])
    app.run()
```
# How to use it

To implement SAPL into a Flask project the functions, which shall be enforced by SAPL have to be decorated with SAPL decorators.
The decorator have to be the first decorator of a function. There are 3 possible decorators, which can be used for a function.

- `pre_enforce` when a function shall be enforced, before it is called.
- `post_enforce` when the function is already executed and the return_value is needed to determine if the requesting client has access to these data.
- `pre_and_post_enforce` when the function is enforced before and after it is called. This decorator can be used,
when the return value of the function is needed to finally decide if access can be granted, but the execution of the 
function is expensive and there are certain parameters of a request, which can already be used to deny access before the 
return value is known.

an example for a pre_enforced function would be:
```Python
from sapl_base.decorators import pre_enforce

@pre_enforce
def pre_enforced_function(*args,**kwargs):
    return_value = "Do something"
    return return_value
```

A decorated function will use the default implementation to create a subject,action and resources of an Authorization Subscription.
If no subject_functions are provided the subject is always "anonymous".

subject, action and resources are dictionarys, which are json dumped with a default JSON Converter.
These 3 dictionarys json formatted contain these values:
<!--- hilfreich wäre hier ein Beispiel (siehe oben) mit dem daraus resultierenden JSON -->

```json
{
  "subject": "is determined by the subject_functions",
  
  "action": {
    "function": {
      "function_name": "name of the function"
    },
    "request": {
      "path": "request.path",
      "method": "request.method",
      "endpoint": "request.endpoint",
      "route": "request.root_url",
      "blueprint": "request.blueprint"
    }
  },
  "resources": {
    "function": {
      "kwargs": "arguments with which the decorated function was called"
    },
    "request": {
      "GET" : "Arguments of the GET Request",
      "POST" : "Arguments of the POST Request"
    },
    "return_value": "Returnvalue of the decorated function"
  }
}
```
To determine, who should have access to what values, Policies have to be written, which are used by the SAPL Server 
to evaluate the Decision for an Authorization Subscription.

Decisions can contain Obligations and Advices, which are in details explained in the section [Obligations and Advices].(#obligations-and-advices)
More Information about SAPL Server, Authorization Subscriptions, Obligations and Advices can be found in the 
[SAPL documentation](https://sapl.io/documentation)

SAPL_Flask does also support writing custom functions for the subject,action and/or resources of an Authorization 
Subscription, as well as providing values for these parameters, which replaces the default functions for these values.

## Providing arguments to a decorator

Instead of using the default implementation on how the subject,action and/or resources are created, it is possible to 
use values, or create your own functions to determine these values.
An example on how a create a constant value for 'action' for a decorated function would be:
```Python
from sapl_base.decorators import pre_enforce

@pre_enforce(action="custom action")
def pre_enforced_function(*args,**kwargs):
    return_value = "Do something"
    return return_value
```
Whenever this function is called, it will be enforced before it is executed.
The value of 'action' parameter of the Authorization Subscription will always be "custom action"

A more dynamic approach could get the type and path of the request, create a dictionary from these values and set this 
dictionary as action.
```Python
from flask import request
from sapl_base.decorators import pre_enforce

def create_action():
  # python ist eine einfache Sprache ;-)
  return {"method": request.method, "path": request.path}

# Beispiel ist nicht sehr selbs sprechen
@pre_enforce(action=create_action)
def pre_enforced_function(*args,**kwargs):
    return_value = "Do something"
    return return_value
```


# Obligations and Advices
<!--- hier ist irgendwie noch ein Doppler mit dem Text unten "How to create ConstraintHandlerProvider" -->


Decisions received from the PDP can contain Obligations and Advices, which have to, or should be handled.
These two categories are called constraints, for which this library offers abstract classes from which can be inherited to 
handle these constraints. The Abstract classes are:

- `ErrorConstraintHandlerProvider`
- `OnDecisionConstraintHandlerProvider`
- `FunctionArgumentsConstraintHandlerProvider`
- `ResultConstraintHandlerProvider`

They all inherit from the class `ConstraintHandlerProvider` and only differ in the types of the arguments their methods take and return.

## Handling of Constraints

A Decision from the PDP can have Constraints attached to the Decision. There are two different kinds of Constraints,
Obligations and Advices. Obligations have to be handled, otherwise the Permission is Denied. Advices should be handled, 
but the Decision won't change when the Advices are not handled.

To handle these Constraints, this library offers an abstract class called `ConstraintHandlerProvider`, which can handle 
Constraints. The classes, which can handle the constraints are created by the developer and have to be registered to be available 
to the library to check, if given constraints can be handled.


## How to create ConstraintHandlerProvider

In order to create ConstraintHandlerProvider, 4 abstract ConstraintHandlerProvider are available to inherit from. These
abstract classes are: 

- `ErrorConstraintHandlerProvider`
- `OnDecisionConstraintHandlerProvider`
- `FunctionArgumentsConstraintHandlerProvider`
- `ResultConstraintHandlerProvider`

They all inherit from the baseclass `ConstraintHandlerProvider` and only differ in the types of the arguments their methods
take and return.

The Baseclass is defined like this:
```python
class ConstraintHandlerProvider(ABC):
  
    @abstractmethod
    def priority(self) -> int:
        """
        ConstraintHandlerProvider are sorted by the value of the priority, when the ConstraintHandlerBundle is created

        :return: value by which ConstraintHandlerProvider are sorted
        """
        return 0

    @abstractmethod
    def is_responsible(self, constraint) -> bool:
        """
        Determine if this ConstraintHandler is responsible for the provided constraint

        :param constraint: A constraint, which can be an Obligation or an Advice, for which the
        ConstraintHandlerProvider checks if it is responsible to handle it.
        :return: Is this ConstraintHandlerProvider responsible to handle the provided constraint
        """
        pass

    @abstractmethod
    def handle(self, argument):
        """
        Abstractmethod, which needs to be implemented by a ConstraintHandlerProvider
        :param argument: The argument, which is provided to the ConstraintHandler, when it is called. This argument can 
        be an Exception, function, decision, or the result of the executed function.
        """
        # Verstehe ich nicht, warum sollte ein ConstraingHandlerProvider Exception oder function handeln. Verstehe nicht den Sinn wann und warum er aufgerufen werden sollte.
        # Bei Decisions macht es Sinnd, das kennen wir ja aus der Java implementierung
```

When a Decision contains a Constraints the library checks all registered ConstraintHandlerProvider, if their 
`is_responsible` method evaluates to true for the given Constraint. 
The responsible Constraint-handler Provider are gathered and 
sorted by the value their method `priority` returns.
At the end, the `handle` methods of the sorted list of `ConstraintHandlerProvider`, which are responsible for a given 
Constraint are executed in the order of the list.

An example for a ConstraintHandlerProvider, which logs the received Decision, when it contains a constraint which 
equals to "log decision" would be:
```python
class LogNewDecisionConstraintHandler(OnDecisionConstraintHandlerProvider):

    def handle(self, decision: Decision) -> None:
        # .__str__() ist private undsollte nicht notwendig sein. Im zweifel str() verwenden.
        logging.info(decision)

    def priority(self) -> int:
        return 0

    def is_responsible(self, constraint) -> bool:
        return True if constraint == "log decision" else False
```

## How to register ConstraintHandlerProvider

The class `ConstraintHandlerService` handles any Constraints and contains a singleton(constraint_handler_service), which 
is created when the file is loaded. All `ConstraintHandlerProvider` registered at this singleton are taken into account, 
when a Decision containing Constraints is checked, if the Constraints can be handled.

The ConstraintHandlerService has methods to register single ConstraintHandlerProvider, or lists of ConstraintHandlerProvider 
for each of the 4 types of ConstraintHandlerProvider.

The following code would initialize the library, register the previously created ConstraintHandlerProvider and launch 
the Flask app.

```Python
import sapl_flask
from sapl_base.constraint_handling.constraint_handler_service import constraint_handler_service
from flask import Flask


app = Flask(__name__)
def subject_function(values:dict):
  # function_name ist fachlich kein subject, siehe oben
  return {"function_name" : values.get("function").__name__}

if __name__ == "__main__":
    sapl_flask.init_sapl(app.config, [subject_function])
    # woher kommt hier der LogNewDecisionConstraintHandler? Import fehlt
    constraint_handler_service.register_decision_constraint_handler_provider(LogNewDecisionConstraintHandler())
    app.run()
```

# How to migrate

If you have an existing project of Flask, you can add SAPL_Flask by installing and initializing the library.
The library can then be used by decorating functions and writing policies.

