from abc import ABC, abstractmethod
from base64 import b64encode

import aiohttp
import requests

from sapl_base.authorization_subscriptions import AuthorizationSubscription


class PolicyDecisionPoint(ABC):

    # TODO: read how to get data from pyproject.toml file ( look at lib/site-packages/_pytest/config/findpaths.py )
    # TODO: get configuration for from_settings(cls) from pyproject.toml

    @classmethod
    def from_settings(cls):
        """
        reads the configuration in the pyproject.toml file and creates a PolicyDecisionPoint depending on the configuration
        """
        # TODO: read config from .toml file and decide which PDP
        return RemotePolicyDecisionPoint()

    @classmethod
    def dummy_pdp(cls):
        """
        :returns a DummyPolicyDecisionPoint, which always returns a 'PERMIT'
        """
        return DummyPolicyDecisionPoint()

    @abstractmethod
    async def decide(self, subscription, decision_events="decide"):
        """
        async function to make a request to a pdp with the given subscription and event to create a stream of decisions

        :param subscription: authorization_subscription which will be sent to a pdp to receive decisions based on it
        :param decision_events: what kind of decision will be requested from the pdp. defaults to 'decide'
        """
        pass

    @abstractmethod
    async def decide_once(self, subscription: AuthorizationSubscription, decision_events="decide"):
        """
        async function to make a request to a pdp with the given subscription and event to receive a
        single decision

        :param subscription: authorization_subscription which will be sent to a pdp to receive decisions based on it
        :param decision_events: what kind of decision will be requested from the pdp. defaults to 'decide'
        """
        pass

    @abstractmethod
    def sync_decide(self, subscription: AuthorizationSubscription, decision_events="decide"):
        """
        synchronous function to make a request to a pdp with the given subscription and event to receive a
        single decision

        :param subscription: authorization_subscription which will be sent to a pdp to receive decisions based on it
        :param decision_events: what kind of decision will be requested from the pdp. defaults to 'decide'
        """
        pass

    # @abstractmethod
    # def sync_decide_once(self, subscription: AuthorizationSubscription, decision_events="decide"):
    #    pass


class DummyPolicyDecisionPoint(PolicyDecisionPoint):
    """
    Dummy settings to run the application without SAPL-Remote-Server, all will be PERMIT in this case
    """

    def __init__(self):
        super(DummyPolicyDecisionPoint, self).__init__()
        # self.logger = logging.getLogger(__name__)
        # self.logger.warning(
        #     "ATTENTION THE APPLICATION USES A DUMMY PDP. ALL AUTHORIZATION REQUEST WILL RESULT IN A SINGLE "
        #     "PERMIT DECISION. DO NOT USE THIS IN PRODUCTION! THIS IS A PDP FOR TESTING AND DEVELOPING "
        #     "PURPOSE ONLY!"
        # )

    async def decide(self, subscription, decision_events="decide"):
        """
        implementation of decide, which always yields a PERMIT
        """

        yield {"decision": "PERMIT"}

    async def decide_once(
            self, subscription: AuthorizationSubscription, decision_events="decide"
    ):
        """
        implementation of decide_once, which always returns a PERMIT
        """
        return {"decision": "PERMIT"}

    def sync_decide(self, subscription: AuthorizationSubscription, decision_events="decide"):
        """
        implementation of sync_decide, which always returns a PERMIT
        """
        return {"decision": "PERMIT"}


class RemotePolicyDecisionPoint(PolicyDecisionPoint, ABC):
    headers = {"Content-type": "application/json"}

    def __init__(self, base_url="http://localhost:8443/api/pdp/",
                 key="YJidgyT2mfdkbmL", secret="Fa4zvYQdiwHZVXh", verify=False):
        self.base_url = base_url
        self.verify = verify
        if (self.verify is None) or (self.base_url is None):
            raise Exception("No valid configuration for the PDP")
        if key is not None:
            key_and_secret = b64encode(str.encode(f"{key}:{secret}")).decode("ascii")
            self.headers["Authorization"] = f"Basic {key_and_secret}"

    # def _sync_request(self, subscription, decision_events):
    #     stream_response = requests.post(
    #         self.base_url + decision_events,
    #         subscription,
    #         stream=True,
    #         verify=self.verify,
    #         headers=self.headers
    #     )
    #     return stream_response

    def sync_decide(self, subscription: AuthorizationSubscription,
                    decision_events="decide"):
        """
        Makes a synchronous request to the set pdp and returns a decision for the sent authorization_subscription

        :param subscription: An Authorization_Subscription which will be sent to the set pdp to receive decisions
        :param decision_events: Signal to tell the PDP what kind of Authorization_Subscription is sent
        and what kind of decision is expected
        """
        with requests.post(
                self.base_url + decision_events,
                subscription,
                stream=True,
                verify=self.verify,
                headers=self.headers
        ) as stream_response:
            # with self._sync_request(
            #         subscription, decision_events
            # ) as stream_response:
            if stream_response.status_code == 204:
                return {"decision": "DENY"}
                # return
            elif stream_response.status_code != 200:
                return {"decision": "DENY"}
                # return
            else:
                lines = b''
                for line in stream_response.content:
                    lines += line
                    if lines.endswith(b'\n\n'):
                        line_set = lines.splitlines(False)
                        response = ''
                        for item in line_set:
                            response += item.decode('utf-8')
                        if response == {"decision": "INDETERMINATE"}:
                            return {"decision": "DENY"}

    # def sync_decide_once(self, subscription: AuthorizationSubscription, decision_events="decide"):
    #    decision = self.sync_decide(subscription, decision_events)
    #    if decision == {"decision": "INDETERMINATE"}:
    #        return {"decision": "DENY"}
    #    return decision

    async def decide(self, subscription, decision_events="decide"):
        """
        Makes a request to the set pdp and returns a stream of decisions for the sent authorization_subscription

        :param subscription: An Authorization_Subscription which will be sent to the set pdp to receive decisions
        :param decision_events: Signal to tell the PDP what kind of Authorization_Subscription is sent
        and what kind of decisions is expected
        """
        async with aiohttp.ClientSession(raise_for_status=True
                                         ) as session:
            async with session.get('http://localhost:8080/') as response:
                # self.base_url + decision_events, data=subscription, verify_ssl=self.verify,
                # headers=self.headers)
                if response.status == 204:
                    yield {"decision": "INDETERMINATE"}
                    # return
                elif response.status != 200:
                    yield {"decision": "INDETERMINATE"}
                    # return
                else:
                    lines = b''
                    async for line in response.content:
                        lines += line
                        if lines.endswith(b'\n\n'):
                            line_set = lines.splitlines(False)
                            response = ''
                            for item in line_set:
                                response += item.decode('utf-8')
                            yield response
                            lines = b''

    async def decide_once(
            self, subscription: AuthorizationSubscription, decision_events="decide"
    ):
        """
        Makes a request to the set pdp and returns the first decision received for the sent authorization_subscription

        :param subscription: An Authorization_Subscription which will be sent to the set pdp to receive a decision
        :param decision_events: Signal to tell the PDP what kind of Authorization_Subscription is sent
        and what kind of decision is expected
        :return: A decision for the given Authorization_Subscription
        """
        decision_stream = self.decide(subscription, decision_events)
        try:
            decision = await decision_stream.__anext__()
            await decision_stream.aclose()
            if decision == {"decision": "INDETERMINATE"}:
                return {"decision": "DENY"}
        except Exception as e:
            return {"decision": "DENY"}
        return decision


pdp = PolicyDecisionPoint.from_settings()
