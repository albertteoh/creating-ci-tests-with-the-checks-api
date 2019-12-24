Changes by Version
==================

2.21.2 (unreleased)
-------------------

- Nothing yet.


2.21.1 (2019-12-20)
-------------------

- Update version correctly.


2.21.0 (2019-12-20)
-------------------

- Clarify reporting error logs ([#469](https://github.com/jaegertracing/jaeger-client-go/pull/469)) -- Yuri Shkuro
- Do not strip leading zeros from trace IDs ([#472](https://github.com/jaegertracing/jaeger-client-go/pull/472)) -- Yuri Shkuro
- Chore (docs): fixed a couple of typos ([#475](https://github.com/jaegertracing/jaeger-client-go/pull/475)) -- Marc Bramaud
- Support custom HTTP headers when reporting spans over HTTP ([#479](https://github.com/jaegertracing/jaeger-client-go/pull/479)) -- Albert Teoh


2.20.1 (2019-11-08)
-------------------

Minor patch via https://github.com/jaegertracing/jaeger-client-go/pull/468

- Make `AdaptiveSamplerUpdater` usable with default values; Resolves #467
- Create `OperationNameLateBinding` sampler option and config option
- Make `SamplerOptions` var of public type, so that its functions are discoverable via godoc

