from abc import abstractmethod, ABC

from .authorization_subscriptions import AuthorizationSubscription, MultiSubscription


class AuthorizationSubscriptionFactory(ABC):
    """
    Baseclass of an AuthorizationSubscriptionFactory, which can be inherited to create a framework specific
    AuthorizationSubscriptionFactory.
    """

    def _create_subscription(self, values: dict, subject=None, action=None, resource=None, environment=None,
                             default_subject_function=None, default_action_function=None,
                             default_resource_function=None,
                             default_environment_function=None):
        """
        Create an authorization_subscription for the decorated function with the arguments provided to the decorator

       :param values: Dictionary which contains data related to the decorated function (class if present, function and dict with named args )
        :param subject: subject with which the function was decorated. None if not specified
        :param action:  action with which the function was decorated. None if not specified
        :param resource: resource with which the function was decorated. None if not specified
        :param environment: environment with which the function was decorated. None if not specified
        :param default_subject_function: Function which will be called with values as parameter to define subject, if no subject was provided to the decorator
        :param default_action_function: Function which will be called with values as parameter to define action, if no action was provided to the decorator
        :param default_resource_function: Function which will be called with values as parameter to define resource, if no resource was provided to the decorator
        :param default_environment_function: Function which will be called with values as parameter to define environment, if no environment was provided to the decorator
        :return: An authorization_subscription which can be sent to a pdp to get an authorization_decision
        """
        if not all((default_subject_function, default_action_function, default_resource_function,
                    default_environment_function)):
            raise Exception

        if subject is not None:
            _subject = self._argument_is_callable(subject, values)
        else:
            _subject = default_subject_function(values)

        if action is not None:
            _action = self._argument_is_callable(action, values)
        else:
            _action = default_action_function(values)

        if resource is not None:
            _resource = self._argument_is_callable(resource, values)
        else:
            _resource = default_resource_function(values)

        if environment is not None:
            _environment = self._argument_is_callable(environment, values)
        else:
            _environment = default_environment_function(values)

        return AuthorizationSubscription(self._remove_empty_dicts(_subject), self._remove_empty_dicts(_action),
                                         self._remove_empty_dicts(_resource),
                                         self._remove_empty_dicts(_environment))

    @staticmethod
    def _argument_is_callable(argument, values: dict):
        """
        Checks if the given argument is a callable and calls it with the given dictionary of values as argument

        :param argument: given argument which was provided to the SAPL Decorator as argument for certain parameter
        :param values: dictionary of the values which are used to create the authorization_subscription
        :return: given argument if it is not a callable, otherwise the return-value of the argument called with values
        """
        if callable(argument):
            return argument(values)
        else:
            return argument

    @abstractmethod
    def _identify_type(self, values: dict):
        """
        Identify depending on the used Framework, which kind of function was decorated.

        Depending on the function create an according authorization_subscription for the PDP

        :param values: dictionary which contains class,function and named args of the decorated function
        """
        pass

    @abstractmethod
    def _valid_combinations(self, fn_type, enforcement_type):
        pass

    def create_authorization_subscription(self, values: dict, subject, action, resource,
                                          environment, scope, enforcement_type):
        """
        Create an authorization_subscription with the given dictionary and arguments

        The returned authorization_subscription is dependent of the framework and the decorated function

        :param enforcement_type:
        :param scope: Argument which creates a AuthorizationSubscription according to the given scope instead of evaluating the scope based on other parameter
        :param values: Dictionary which contains data related to the decorated function (class if present, function and dict with named args )
        :param subject: subject with which the function was decorated. None if not specified
        :param action:  action with which the function was decorated. None if not specified
        :param resource: resource with which the function was decorated. None if not specified
        :param environment: environment with which the function was decorated. None if not specified
        :return: An authorization_subscription which can be sent to a pdp to get an authorization_decision
        """
        fn_type: str
        if scope == "automatic":
            fn_type = self._identify_type(values)
        else:
            fn_type = scope
        self._valid_combinations(fn_type, enforcement_type)
        return self._create_subscription_for_type(fn_type, values, subject, action, resource, environment, scope)

    @abstractmethod
    def _create_subscription_for_type(self, fn_type, values: dict, subject, action, resource,
                                      environment, scope) -> AuthorizationSubscription:
        """
        Calls implementations on how to create an authorization_subscription for the given type of called function

        :param scope: Argument which creates a AuthorizationSubscription according to the given scope instead of evaluating the scope based on other parameter
        :param fn_type: What type of function was annotated e.g. function which renders a view, or a function which makes a database call to get values for a view.
        :param values: Dictionary which contains data related to the decorated function (class if present, function and dict with named args )
        :param subject: subject with which the function was decorated. None if not specified
        :param action:  action with which the function was decorated. None if not specified
        :param resource: resource with which the function was decorated. None if not specified
        :param environment: environment with which the function was decorated. None if not specified
        """
        pass

    def _remove_empty_dicts(self, dictionary: dict):
        """
        A helper function to prevent empty dictionary's from being added to the authorization_subscription

        :param dictionary: A dictionary which will be stripped of it's empty dictionary's
        :return: The given dictionary stripped of empty dictionary's inside itself, or None if the given dictionary is empty
        """
        dict_copy = dictionary.copy()
        for k, v in dictionary.items():
            if isinstance(v, dict):
                dict_copy[k] = self._remove_empty_dicts(v)

            if dict_copy[k] is None:
                dict_copy.pop(k)

        if not dict_copy:
            return None

        return dict_copy


class MultiSubscriptionBuilder:
    """
    Can be used to create a Multi subscription by adding single Authorization_subscription
    """
    SUBJECT_ID = "subjectID"
    ACTION_ID = "actionID"
    RESOURCE_ID = "resourceID"
    ENVIRONMENT_ID = "environmentID"
    AUTHORIZATION_SUBSCRIPTION_ID = "authorization_subscriptionID"

    def __init__(self):
        self._built = False
        self.subject = []
        self.action = []
        self.resource = []
        self.environment = []
        self.authorization_subscription = []

    def with_authorization_subscription(self, authorization_subscription: AuthorizationSubscription):
        """
        Adds the given AuthorizationSubscription to the MultiSubscriptionBuilder
        :param authorization_subscription: AuthorizationSubscription, which will be added to the MultiSubscriptionBuilder
        """
        dic = dict()
        self._add_subject(authorization_subscription, dic)
        self._add_action(authorization_subscription, dic)
        self._add_resource(authorization_subscription, dic)
        self._add_environment(authorization_subscription, dic)
        self.authorization_subscription.append({authorization_subscription.subscription_id: dic})

    def _add_subject(self, authorization_subscription: AuthorizationSubscription, dictionary: dict):
        if authorization_subscription.subject:
            self.subject.append(authorization_subscription.subject)
            dictionary[self.SUBJECT_ID] = len(self.subject) - 1

    def _add_action(self, authorization_subscription: AuthorizationSubscription, dictionary: dict):
        if authorization_subscription.action:
            self.action.append(authorization_subscription.action)
            dictionary[self.ACTION_ID] = len(self.action) - 1

    def _add_resource(self, authorization_subscription: AuthorizationSubscription, dictionary: dict):
        if authorization_subscription.resource:
            self.resource.append(authorization_subscription.resource)
            dictionary[self.RESOURCE_ID] = len(self.resource) - 1

    def _add_environment(self, authorization_subscription: AuthorizationSubscription, dictionary: dict):
        if authorization_subscription.environment:
            self.environment.append(authorization_subscription.environment)
            dictionary[self.ENVIRONMENT_ID] = len(self.environment) - 1

    @staticmethod
    def _remove_empty_list(subscription_list):
        """
        Helper function to remove empty lists

        :param subscription_list: A list which contains arguments, which will
        be passed to a Multi subscription as arguments
        :return: None if the list is empty, otherwise the given list.
        """
        if not subscription_list:
            return None
        return subscription_list

    def build(self):
        """
        :return: A multi subscription created from the given Authorization_subscriptions
        """
        if self._built:
            raise Exception("already built")
        self._built = True
        return MultiSubscription(self._remove_empty_list(self.subject), self._remove_empty_list(self.action),
                                 self._remove_empty_list(self.resource), self._remove_empty_list(self.environment),
                                 self._remove_empty_list(self.authorization_subscription))


auth_factory = None
