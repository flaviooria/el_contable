# Functional Requirements

## Overview
El Contable helps users manage personal finances by importing account movements, tracking income and expenses, and showing how much money remains available.
This document describes product capabilities and stable business rules.
Implementation strategies and architectural decisions belong in OpenSpec, ADRs, or `ARCHITECTURE.md`.

## Account Movement Import
Users can upload account movements using:
- `.xlsx`
- `.csv`

The application may provide a basic spreadsheet template to help users prepare compatible files.
The system must extract the transaction information required by the application.
At minimum, movements should support:
- amount;
- description or comment;
- transaction date when available.

The system must distinguish between money entering and leaving the account.

## Duplicate Movements
The system must prevent duplicate movements from being persisted.
Uploading overlapping account data must not create redundant transactions.
The exact detection and import strategy is defined in the movement upload specification and relevant ADR.

## Uploaded File Handling
Uploaded files are temporary.
Once the required information has been processed, the original uploaded file must not be retained unnecessarily.
Persisted accounting data is independent from the uploaded source file.

## Balance
The application must be able to determine the amount of money currently available to the user.
The available balance must reflect persisted income and expenses.
When movement imports overlap with previously imported data, duplicated transactions must not alter the resulting balance.

## Income and Expenses
The application must support tracking:
- income;
- fixed expenses;
- variable expenses.

Users must be able to define or classify expenses as fixed or variable.
The system may support either a fixed monthly reference amount or a variable amount depending on the financial model adopted by the product.

## Expense Categories
Expenses may be associated with categories.
Categories are used to aggregate expenses for reporting and dashboard visualizations.

## Dashboard
The application must provide financial dashboards.
At minimum, users should be able to visualize:
- income vs expenses;
- expenses by category;
- remaining money.

Dashboard information must be derived from the user's persisted financial data.

## Virtual Piggy Banks
Users can create virtual piggy banks to reserve part of their available money for specific purposes.
Money allocated to a piggy bank must be reflected in the amount considered available for general spending.
Piggy banks are linked to the user's financial allocation model.
Changes to piggy-bank allocations must cause the corresponding available balance to be recalculated.

## Detailed Feature Specifications
Detailed behaviour for individual features is defined under:
`openspec/specs/`

For movement uploads, see:
`openspec/specs/upload_movements/spec.md`

Implementation strategy and architectural rationale must not be duplicated in this document.