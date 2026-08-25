# API reference

## Core

::: road_centerline.core.compute_centerlines

::: road_centerline.core.process_file

## Attributes

::: road_centerline.attributes.add_road_attributes

## Robustness

::: road_centerline.validate.repair_geometries

::: road_centerline.validate.find_unusable

## Network

::: road_centerline.network.build_network

::: road_centerline.network.to_networkx

## CRS

::: road_centerline.crs.resolve_working_crs

## Densification

::: road_centerline.densify.densify_geometry

::: road_centerline.densify.densify_geoseries

## Formats

See [Supported formats](quickstart.md#supported-formats) for context on
when `driver` is needed.

::: road_centerline.formats.resolve_output_driver

## Exceptions

::: road_centerline.exceptions.MissingCRSError

::: road_centerline.exceptions.AmbiguousDriverError

## CLI

The CLI (`road-centerline`) mirrors `process_file`'s parameters. See
[Quickstart](quickstart.md#cli-usage) or run:

```sh
road-centerline --help
```
